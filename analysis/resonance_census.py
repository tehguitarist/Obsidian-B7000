#!/usr/bin/env python3.11
"""GATE AM — THE RESONANCE CENSUS: what in this chain can resonate at all, and where.

WHY THIS EXISTS (session 145, executing s141's own closing sentence and s144's `NEXT` #4).

  Item 6's brief has been narrowed to a POSITIVE specification.  AL5 (s141) established that a
  **complex pole pair** is the one structure that clears gate 5's real-pole bound (a sum of f^2
  terms is still f^2, so no number of real poles helps), and derived where such a pair would have
  to sit:

      Q/damping route : a resonance at ~2.3-2.8 kHz with the vertex on its UPPER skirt
      f0-move route   : a resonance at ~3.2-5.8 kHz

  AL5 then checked the two shipped Sallen-Keys and found 0 of 2.  And CLAUDE.md's own summary of
  that result ends with the sentence this gate exists to answer:

      "Nothing has yet asked what in this chain could resonate near 2.5 kHz at all — that is the
       buildable next question."

  AL5 screened the only two structures it had closed forms for.  This gate screens **every stage
  in the signal path**, and it does so by computing natural frequencies rather than by inspecting
  transfer-function shapes -- so a resonance cannot hide behind a feature that happens to look
  smooth on a magnitude plot.

⭐⭐ THE INSTRUMENT, AND WHY IT IS UNIFORM ACROSS STAGES THAT LOOK NOTHING ALIKE.
  Every stage in this chain is a linear network of resistors, capacitors and ideal/finite-gain
  controlled sources, so its MNA system is **affine in s**:

      A(s) . x = b(s) ,      A(s) = G + s*C

  The natural frequencies are the roots of det(G + s*C) = 0, i.e. the finite generalised
  eigenvalues of the pencil (-G, C).  That is one construction for the treble ladder, the clipper
  loop, a Sallen-Key and a Baxandall alike -- no per-stage algebra, no fitting, no rootfinding on
  a magnitude curve, and singular C (a stage with fewer caps than nodes) is handled by the QZ
  algorithm returning infinite eigenvalues, which are exactly the non-existent modes.

  ⭐ THE STRUCTURAL RESULT THE CENSUS RESTS ON (AM3): a network of **resistors and capacitors
  only** has G and C both SYMMETRIC POSITIVE SEMI-DEFINITE, so the pencil is symmetric-definite
  and **every natural frequency is real and non-positive**.  Resonance requires an inductor (there
  are none anywhere in this pedal) or a controlled source arranged to feed energy back.  So the
  census reduces to a question about the ACTIVE stages, and the gate asserts the passive half
  numerically rather than citing the theorem at it.

⭐⭐ WHAT MAKES THE NETLISTS TRUSTWORTHY, given `rebuild-targets-dont-transcribe`.
  The topology is written here as a netlist (readable against circuit.md's node graphs), but **no
  component VALUE is retyped**: every value is pulled out of `eq_reference`'s own function
  signatures with `inspect.signature`, or out of `FitParams.h` through GATE AB's reader, so a
  future re-fit cannot desynchronise this gate.  And the topology itself is not trusted either --
  AM1 requires each netlist's transfer function to reproduce `eq_reference`'s already-validated
  oracle to 1e-11 relative, over the full band and at every switch position.  A mis-stamped node
  fails that immediately.

WHAT THIS GATE DOES **NOT** CLAIM.
  * It censuses the SHIPPED MODEL.  A structure the model omits cannot appear in it -- which is
    the point of AM6, where the one omitted positive-feedback structure in the circuit (the C4
    bootstrap around Q2) is named and sized rather than left as a gap.
  * "No resonance in the model" is not "no resonance in the device".  The deliverable is a frame
    result about where item 6's carrier can possibly live, not a measurement of the pedal.
  * AM4's clipper proof is about the SMALL-SIGNAL loop.  It says the linearised loop cannot
    resonate at any parameter values; it says nothing about the VTC's own nonlinearity.
  * No constant, no `src/` edit, no render, no new capture.

  AM1  KNOWN ANSWERS  (a) every netlist reproduces eq_reference's oracle (bar 1e-11 relative);
                      (b) TWO-SIDED synthetic control -- an RC ladder whose poles are known real,
                          and a biquad whose pole pair is known complex, so the classifier can
                          fail in both directions;
                      (c) the two Sallen-Keys' (f0, Q) from the EIGENVALUES must reproduce AL5's
                          own closed form, tying this instrument to the gate it extends.
  AM2  THE CENSUS     every stage, in signal order, with its position relative to the clipper,
                      its order, and every natural frequency classified real / complex.
  AM3  THE PASSIVE    the RC theorem asserted on the shipped stamps: symmetry + PSD + Im == 0,
       HALF           with the bar taken from AM1b's own measured numerical floor (s113's rule),
                      and a mutation control proving the check can fail.
  AM4  THE CLIPPER    the at-clipper loop's discriminant is >= 0 for ALL R16, R18, Cg, C14, a0 --
                      proved by AM-GM and verified over a random parameter sweep, so the result
                      is a property of the TOPOLOGY, not of the shipped values.
  AM5  VERDICT        computed: every complex pair found, graded against AL5's admissible bands
                      (imported from the stored report, never transcribed) AND against its
                      position relative to the clipper.
  AM6  WHAT IS OMITTED the positive-feedback structures the model does not carry, named and sized.

Usage:
  python3.11 analysis/resonance_census.py
  python3.11 analysis/resonance_census.py --json analysis/reports/s145_resonance_census.json
"""
import argparse
import contextlib
import inspect
import io
import json
import math
import os
import sys

import numpy as np
from scipy.linalg import eig

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

# eq_reference prints a large reference dump at MODULE level (it has no __main__ guard) -- the
# same suppression GATE AJ uses, for the same reason.
with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ            # noqa: E402  the validated per-stage oracles
    import bt_pair_shape_gate as AB      # noqa: E402  FitParams reader, SK values, clipA0
    import at_clipper_tilt_gate as AI    # noqa: E402  grunt_caps() -- the COMPOSED cap values

_fp = AB._read_fitparam                  # `double <name> = ...;` out of FitParams.h, or refuse

AL_REPORT = os.path.join(HERE, "reports", "s141_deficit_exponent.json")
OUT_JSON = os.path.join(HERE, "reports", "s145_resonance_census.json")

# AM1a's bar.  Two independent nodal formulations of one network agree to round-off; 1e-11
# relative is ~3 decades above the observed residual and ~5 below any topology error.
KA_TF_TOL = 1e-11
# AM4's random sweep size.  The proof is algebraic; the sweep is the mutation-proof that the
# algebra was transcribed correctly, so it only has to be large enough to be non-vacuous.
AM4_TRIALS = 20000

# Frequencies the transfer known answer is checked at.  Deliberately spans well past the audio
# band at both ends: a stamp error at a node with a small cap only shows where that cap matters.
KA_F = np.logspace(0.0, 5.3, 401)


def _die(msg):
    print(f"\n⛔ GATE AM REFUSES: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Values.  NOTHING here is a retyped component value -- they come from the
# oracle's own signature or from FitParams.h.
# ---------------------------------------------------------------------------
def defaults(fn):
    """The oracle's own default component values, by name."""
    return {k: v.default for k, v in inspect.signature(fn).parameters.items()
            if v.default is not inspect.Parameter.empty}


TA = defaults(EQ.treble_attack_tf)       # the DRAWN treble values (schematic)
JF = defaults(EQ.jfet_stage_lin_tf)
JZ = defaults(EQ.jfet_source_z)
DR = defaults(EQ.drive_stage_tf)
BT = defaults(EQ.bridged_t_tf)
MID = defaults(EQ.mid_stage_tf)
BX = defaults(EQ.baxandall_tf)


# ⚠⚠ The SHIPPED treble/ATTACK stage is NOT the drawn one.  Session 99/100 re-fitted 17
# constants AND changed the topology: R8/R11 became a 4-resistor TAP LADDER the switch selects
# from, the C5 leg gained a damping resistor and a per-throw trim, and `trebleC8` ships at 0
# (C8 removed from circuit entirely).  Censusing `eq_reference`'s defaults would therefore be
# `verify-the-BASELINE-not-its-LABEL` — so every value below is read from FitParams.h, and the
# per-throw collapse of the tap ladder is TrebleAttack.h's own (Rtop/Rbot, exact for series
# resistors with no loaded interior node).
def shipped_treble(position):
    """(elements-kwargs) for the shipped stage at one ATTACK throw."""
    ra, rb, rc = _fp("attackTapRa"), _fp("attackTapRb"), _fp("attackTapRc")
    r11 = _fp("attackTapR11")
    rtop = {"boost": ra, "flat": ra + rb, "cut": ra + rb + rc}[position]
    rbot = {"boost": rb + rc + r11, "flat": rc + r11, "cut": r11}[position]
    dflt = _fp("trebleLadderDampR")
    damp = {"boost": _fp("attackDampBoost"), "cut": _fp("attackDampCut"), "flat": -1.0}[position]
    trim = {"boost": _fp("attackC5TrimBoost"), "cut": _fp("attackC5TrimCut"), "flat": 0.0}[position]
    return dict(R7=_fp("trebleR7"), R8=rtop, R11=rbot, R12=_fp("trebleLadderR12"),
                R14=_fp("trebleLadderR14"), R13=TA["R13"],
                C5=_fp("trebleC5") + trim, C9=_fp("trebleC9"), C6=_fp("trebleC6"),
                C7=_fp("trebleC7"), C8=_fp("trebleC8"),
                RdampC5=(damp if damp >= 0.0 else dflt))


CLIP_R16 = _fp("clipR16")                # fitted; AB hardcodes the schematic 6.8k
MID_CAPS = [("LO-MID 250", _fp("midLoCap250"), _fp("midCapRatioLo"), _fp("midWiperRLo")),
            ("LO-MID 500", _fp("midLoCap500"), _fp("midCapRatioLo"), _fp("midWiperRLo")),
            ("LO-MID 1k", _fp("midLoCap1k"), _fp("midCapRatioLo"), _fp("midWiperRLo")),
            ("HI-MID 750", _fp("midHiCap750"), _fp("midCapRatioHi"), _fp("midWiperRHi")),
            ("HI-MID 1k5", _fp("midHiCap1500"), _fp("midCapRatioHi"), _fp("midWiperRHi")),
            ("HI-MID 3k", _fp("midHiCap3k"), _fp("midCapRatioHi"), _fp("midWiperRHi"))]
BAX_R36 = _fp("trebleWiperR")            # fitted 4k7; the drawn R36 is 3k3


def jfet_drain_z():
    """JfetStage::getSourceZ() -> (ro, rq2, rp, cp), the network TrebleAttack stamps at node G."""
    gm, ro, rq2 = _fp("jfetGm"), _fp("jfetRo"), _fp("jfetRq2")
    rp = ro * gm * JZ["R6"]
    return ro, rq2, rp, (JZ["R6"] * JZ["C3"]) / rp


# ---------------------------------------------------------------------------
# A tiny MNA builder.  Elements are (kind, ...) tuples; node 0 is ground.
#
#   ("R", a, b, ohms)              resistor
#   ("C", a, b, farads)            capacitor
#   ("V", n, volts)                ideal source at node n (adds a current unknown)
#   ("I", n, amps)                 ideal CURRENT source into node n (no extra unknown)
#   ("OP", p, m, o)                IDEAL op-amp: nullator (V(p)=V(m)) + norator at o
#   ("VCVS", o, p, m, gain)        finite-gain source: V(o) = gain*(V(p)-V(m))
#
# Every stamp is either s-free (-> G) or proportional to s (-> C), so the system is affine in s
# BY CONSTRUCTION and the pencil needs no numerical differencing to extract.
# ---------------------------------------------------------------------------
class Net:
    def __init__(self, elements, nodes):
        self.nodes = list(nodes)                 # names, ground excluded
        self.idx = {n: i for i, n in enumerate(self.nodes)}
        self.elements = list(elements)
        self.extra = extra = sum(1 for e in elements if e[0] in ("V", "OP", "VCVS"))
        self.n = len(self.nodes) + extra
        self.G = np.zeros((self.n, self.n))
        self.Cm = np.zeros((self.n, self.n))
        self.b_dc = np.zeros(self.n)             # RHS from ("V", ...) sources
        self._build()

    def _k(self, node):
        return None if node == 0 else self.idx[node]

    def _stamp2(self, M, a, b, y):
        ia, ib = self._k(a), self._k(b)
        if ia is not None:
            M[ia, ia] += y
        if ib is not None:
            M[ib, ib] += y
        if ia is not None and ib is not None:
            M[ia, ib] -= y
            M[ib, ia] -= y

    def _build(self):
        k = len(self.nodes)
        for e in self.elements:
            if e[0] == "R":
                self._stamp2(self.G, e[1], e[2], 1.0 / e[3])
            elif e[0] == "C":
                self._stamp2(self.Cm, e[1], e[2], e[3])
            elif e[0] == "V":
                n = self._k(e[1])
                self.G[n, k] += 1.0
                self.G[k, n] += 1.0
                self.b_dc[k] = e[2]
                k += 1
            elif e[0] == "I":
                self.b_dc[self._k(e[1])] += e[2]
            elif e[0] == "OP":
                # nullator: V(p) - V(m) = 0   ;   norator: current unknown injected at o
                p, m, o = self._k(e[1]), self._k(e[2]), self._k(e[3])
                if p is not None:
                    self.G[k, p] += 1.0
                if m is not None:
                    self.G[k, m] -= 1.0
                self.G[o, k] += 1.0
                k += 1
            elif e[0] == "VCVS":
                # V(o) - gain*(V(p)-V(m)) = 0, current unknown injected at o
                o, p, m, g = self._k(e[1]), self._k(e[2]), self._k(e[3]), e[4]
                self.G[k, o] += 1.0
                if p is not None:
                    self.G[k, p] -= g
                if m is not None:
                    self.G[k, m] += g
                self.G[o, k] += 1.0
                k += 1
            else:
                raise ValueError(f"unknown element {e[0]}")

    # -- transfer ----------------------------------------------------------
    def solve(self, f, out_node):
        """V(out_node) at frequencies f, with the ("V", ...) source as the input."""
        s = 2j * np.pi * np.asarray(f, dtype=float)
        j = self.idx[out_node]
        y = np.empty(len(s), dtype=complex)
        for i, si in enumerate(s):
            y[i] = np.linalg.solve(self.G + si * self.Cm, self.b_dc)[j]
        return y

    # -- natural frequencies ----------------------------------------------
    def poles(self):
        """Finite roots of det(G + s*C) = 0, in Hz-domain complex s/(2*pi)."""
        w = eig(-self.G, self.Cm, right=False)
        return np.asarray([p for p in w if np.isfinite(p)], dtype=complex)

    def is_passive_rc(self):
        """True when the stamps contain no controlled source (-> the RC theorem applies)."""
        return all(e[0] in ("R", "C", "V", "I") for e in self.elements)


def classify(poles, tol_ratio):
    """-> list of dicts. A pole is COMPLEX when |Im/Re| exceeds the measured numerical floor."""
    out = []
    for p in poles:
        re, im = float(p.real), float(p.imag)
        ratio = abs(im) / abs(re) if re != 0.0 else float("inf")
        cx = ratio > tol_ratio
        d = {"f_hz": abs(p) / (2.0 * math.pi), "re": re, "im": im,
             "ratio": ratio, "complex": bool(cx)}
        if cx:
            d["q"] = abs(p) / (2.0 * abs(re))
        out.append(d)
    return out


# ---------------------------------------------------------------------------
# The stage netlists.  Topology from circuit.md's node graphs; every VALUE from
# `defaults()` above.  AM1a gates each one against eq_reference.
# ---------------------------------------------------------------------------
def net_treble(position, vals=None, with_source_z=True):
    """The SHIPPED TrebleAttack stage — TrebleAttack.h's own 7-node graph.

        i_drain -> G ;  G --ro-- H --(Rp||Cp)-- GND ;  G --Rq2-- GND     (J201 drain Z)
        G --R7-- M --Rtop-- P --Rbot-- GND                               (collapsed tap rail)
        G --(RdampC5 + C5)-- L1 --C9-- L2 --C6-- M ;  L1--R12--GND ; L2--R14--GND
        P --C7-- Q --R13-- GND                                           (into IC2_A(+))

    `vals=None` uses the shipped constants; pass a dict to evaluate the DRAWN network (AM1a).
    The damping resistor sits in SERIES with C5, so that leg is still one R and one C -- the
    stage stays a passive RC network, which is the whole point.
    """
    v = vals if vals is not None else shipped_treble(position)
    ro, rq2, rp, cp = jfet_drain_z()
    e = [("I", "G", 1.0)]
    if with_source_z:
        e += [("R", "G", "H", ro), ("R", "H", 0, rp), ("C", "H", 0, cp), ("R", "G", 0, rq2)]
    # ⚠ A zero damping resistor is OMITTED, never stamped as a numerical short: TrebleAttack.h's
    # own header records that a 1e-12 ohm short "puts a 1e12 conductance against a 2e-6 rail and
    # the solve loses every digit".  Measured here as 1.5e-03 relative error against the oracle
    # at 1e-9 ohm -- i.e. this exact trap, caught by AM1a rather than reasoned about.
    if v["RdampC5"] > 0.0:
        e += [("R", "G", "Ld", v["RdampC5"]), ("C", "Ld", "L1", v["C5"])]
    else:
        e += [("C", "G", "L1", v["C5"])]
    e += [("R", "G", "M", v["R7"]), ("R", "M", "P", v["R8"]), ("R", "P", 0, v["R11"]),
          ("C", "L1", "L2", v["C9"]), ("C", "L2", "M", v["C6"]),
          ("R", "L1", 0, v["R12"]), ("R", "L2", 0, v["R14"]),
          ("C", "P", "Q", v["C7"]), ("R", "Q", 0, v["R13"])]
    if v["C8"] > 0.0:
        if position == "boost":
            e.append(("C", "M", "P", v["C8"]))       # C8 bridges the top rail
        elif position == "cut":
            e.append(("C", "P", 0, v["C8"]))         # C8 shunts P to ground
    nodes = ["G", "M", "P", "L1", "L2", "Q"] + (["H"] if with_source_z else [])
    if v["RdampC5"] > 0.0:
        nodes.append("Ld")
    return Net(e, nodes), "Q"


def drawn_treble():
    """eq_reference's own defaults, so AM1a compares two formulations of ONE network."""
    return dict(R7=TA["R7"], R8=TA["R8"], R11=TA["R11"], R12=TA["R12"], R14=TA["R14"],
                R13=TA["R13"], C5=TA["C5"], C9=TA["C9"], C6=TA["C6"], C7=TA["C7"],
                C8=TA["C8"], RdampC5=0.0)


def net_bridged_t():
    """Shipped values (btR22/btR23/btC16/btC17 are fitted -- AB reads them from FitParams.h)."""
    return Net([("V", "B", 1.0),
                ("R", "B", "Nmid", AB.BT_R22), ("R", "Nmid", "Nout", AB.BT_R23),
                ("C", "Nmid", 0, AB.BT_C17), ("C", "B", "Nout", AB.BT_C16)],
               ["B", "Nmid", "Nout"]), "Nout"


def net_sk(R1, R2, C1, C2):
    """Vin-R1-X-R2-Y ; C2 Y->gnd ; unity follower Y->O ; C1 from X to O."""
    return Net([("V", "I", 1.0),
                ("R", "I", "X", R1), ("R", "X", "Y", R2), ("C", "Y", 0, C2),
                ("OP", "Y", "O", "O"), ("C", "X", "O", C1)],
               ["I", "X", "Y", "O"]), "O"


def net_clipper(cg, a0):
    """Vs -Cg- A -R16- W ; (R18 || C14) W->O ; O = -a0 * W (finite-gain inverter)."""
    return Net([("V", "S", 1.0),
                ("C", "S", "A", cg), ("R", "A", "W", CLIP_R16),
                ("R", "W", "O", AB.R18), ("C", "W", "O", AB.C14),
                ("VCVS", "O", 0, "W", a0)],
               ["S", "A", "W", "O"]), "O"


def net_drive(rdrive):
    """Non-inverting IC2_A: + = Vin, feedback R15||C10 from - to O, Zg = R17+Rdrive+R32."""
    zg = DR["R17"] + rdrive + DR["R32"]
    return Net([("V", "I", 1.0),
                ("OP", "I", "N", "O"),
                ("R", "N", 0, zg), ("R", "N", "O", DR["R15"]), ("C", "N", "O", DR["C10"])],
               ["I", "N", "O"]), "O"


def net_jfet_gate():
    """Vin -C2- X -R4- G -R5- gnd. The J201 gate draws no current; output is V(G)."""
    return Net([("V", "I", 1.0),
                ("C", "I", "X", JF["C2"]), ("R", "X", "G", JF["R4"]), ("R", "G", 0, JF["R5"])],
               ["I", "X", "G"]), "G"


def net_jfet_out():
    """Q1 drain: ro*k(s) || Rq2, with ro*k(s) = ro + (Rp || Cp), Rp = ro*gm*R6, Rp*Cp = R6*C3.

    JfetStage.h's own realisation ("its nodal matrix: Zout(s) = [ro + (Rp || Cp)] || Rq2"), driven
    by a unit source through the series arm so the natural frequencies of the loaded drain node
    are what comes out.
    """
    ro, gm, rq2 = JZ["ro"], JZ["gm"], JZ["Rq2"]
    rp = ro * gm * JZ["R6"]
    cp = (JZ["R6"] * JZ["C3"]) / rp
    return Net([("V", "I", 1.0),
                ("R", "I", "P", ro), ("R", "P", "D", rp), ("C", "P", "D", cp),
                ("R", "D", 0, rq2)],
               ["I", "P", "D"]), "D"


def net_mid(c_series, ratio, rw, a):
    """circuit.md LO-MID/HI-MID, at the SHIPPED constants: the across-lug cap is a SCALED PAIR
    (C32 = ratio * C33, session 27's A2c-3) and the wiper leg carries a series damping R."""
    rp = MID["Rp"]
    ra, rb = a * rp, (1.0 - a) * rp
    e = [("V", "I", 1.0),
         ("R", "I", "P3", MID["R38"]), ("R", "P1", "O", MID["R39"]),
         ("C", "P3", "P1", ratio * c_series),
         ("R", "P3", "W", ra), ("R", "P1", "W", rb),
         ("R", "I", "N", MID["R41"]), ("R", "N", "O", MID["R40"]),
         ("OP", 0, "N", "O")]
    nodes = ["I", "P3", "P1", "W", "N", "O"]
    if rw > 0.0:                                  # never stamp a zero R as a short (see net_treble)
        e += [("R", "W", "Wd", rw), ("C", "Wd", "N", c_series)]
        nodes.append("Wd")
    else:
        e += [("C", "W", "N", c_series)]
    return Net(e, nodes), "O"


def net_baxandall(ab, at):
    rp = BX["Rp"]
    rba, rbb = ab * rp, (1.0 - ab) * rp
    rta, rtb = at * rp, (1.0 - at) * rp
    return Net([("V", "I", 1.0),
                ("R", "I", "A", BX["R33"]), ("R", "B", "O", BX["R34"]),
                ("C", "A", "Wb", BX["C25"]), ("R", "A", "Wb", rba),
                ("C", "B", "Wb", BX["C26"]), ("R", "B", "Wb", rbb),
                ("R", "Wb", "N", BX["R35"]),
                ("C", "I", "T3", BX["C28"]), ("R", "T3", "Wt", rta),
                ("C", "T1", "O", BX["C29"]), ("R", "T1", "Wt", rtb),
                ("R", "Wt", "N", BAX_R36),
                ("R", "N", "O", BX["R37"]), ("C", "N", "O", BX["C30"]),
                ("OP", 0, "N", "O")],
               ["I", "A", "B", "Wb", "T3", "T1", "Wt", "N", "O"]), "O"


# ---------------------------------------------------------------------------
# AM1 -- known answers
# ---------------------------------------------------------------------------
def _relerr(a, b):
    a, b = np.asarray(a), np.asarray(b)
    den = np.maximum(np.abs(a), np.abs(b))
    keep = den > 0.0
    return float(np.max(np.abs(a[keep] - b[keep]) / den[keep]))


def gate_am1(out):
    print("\n" + "-" * 96)
    print("AM1  KNOWN ANSWERS")
    print("-" * 96)

    # (a) every netlist against eq_reference's own oracle
    print("  (a) each netlist's transfer vs eq_reference's validated oracle "
          f"(bar {KA_TF_TOL:.0e} relative):")
    checks = []
    # The treble stage is checked BOTH ways: at eq_reference's DRAWN defaults (two formulations
    # of one documented network) and at the SHIPPED constants (the tap collapse + damping leg,
    # which the oracle can express because Rtop/Rbot are exactly R8/R11 per throw).
    ro, rq2, _, _ = jfet_drain_z()
    zkw = dict(gm=_fp("jfetGm"), ro=ro, Rq2=rq2)
    # ⚠⚠ AM1a compares my netlist against the oracle AT THE SAME VALUES, so it validates
    # TOPOLOGY and cannot notice if `shipped_treble` quietly returned the drawn set -- both
    # sides would move together and agree perfectly.  That needs its own guard, because
    # censusing the drawn network while calling it shipped is exactly
    # `verify-the-BASELINE-not-its-LABEL`, and s99/s100 re-fitted this stage hard enough that
    # agreement would itself be the bug.
    sh, dr = shipped_treble("flat"), drawn_treble()
    moved = [k for k in dr if abs(sh[k] - dr[k]) > 1e-12 * max(abs(dr[k]), 1e-30)]
    print(f"      shipped-vs-drawn divergence guard: {len(moved)}/{len(dr)} treble values differ "
          f"({', '.join(sorted(moved)[:6])}{'...' if len(moved) > 6 else ''})")
    if len(moved) < 5:
        _die(f"AM1a — only {len(moved)} treble values differ between the shipped and drawn sets; "
             f"s99/s100 re-fitted 17 of them, so this gate is censusing the DRAWN network while "
             f"labelling it shipped")
    for pos in ("flat", "boost", "cut"):
        for lbl, v in (("drawn", drawn_treble()), ("shipped", shipped_treble(pos))):
            net, o = net_treble(pos, vals=v)
            checks.append((f"treble stage [{pos}/{lbl}]", net.solve(KA_F, o),
                           EQ.treble_attack_transimpedance(KA_F, pos, **zkw, **v)))
    net, o = net_bridged_t()
    checks.append(("recovery bridged-T", net.solve(KA_F, o),
                   EQ.bridged_t_tf(KA_F, R22=AB.BT_R22, R23=AB.BT_R23,
                                   C16=AB.BT_C16, C17=AB.BT_C17)))
    for nm, kw in (("Sallen-Key IC4_B", AB.SK_B), ("Sallen-Key IC4_A", AB.SK_A)):
        net, o = net_sk(**kw)
        checks.append((nm, net.solve(KA_F, o), EQ.sallen_key_lpf_tf(KA_F, **kw)))
    caps = AI.grunt_caps()
    for nm, cg in caps.items():
        net, o = net_clipper(cg, AB.CLIP_A0)
        checks.append((f"clipper loop [{nm}]", net.solve(KA_F, o),
                       EQ.clipper_smallsignal_tf(KA_F, cg, A0=AB.CLIP_A0,
                                                 R16=CLIP_R16, R18=AB.R18, C14=AB.C14)))
    for rd in (0.0, 100e3):
        net, o = net_drive(rd)
        checks.append((f"DRIVE stage [Rd={rd/1e3:.0f}k]", net.solve(KA_F, o),
                       EQ.drive_stage_tf(KA_F, rd)))
    for lbl, cser, ratio, rw in (MID_CAPS[2], MID_CAPS[5]):
        for a in (0.5, 0.9):
            net, o = net_mid(cser, ratio, rw, a)
            checks.append((f"mid stage [{lbl} a={a}]", net.solve(KA_F, o),
                           EQ.mid_stage_tf(KA_F, a, cser, C32=ratio * cser, Rw=rw)))
    for ab_, at_ in ((0.5, 0.5), (0.9, 0.2)):
        net, o = net_baxandall(ab_, at_)
        checks.append((f"Baxandall [b={ab_} t={at_}]", net.solve(KA_F, o),
                       EQ.baxandall_tf(KA_F, ab_, at_, R36=BAX_R36)))

    worst = 0.0
    for nm, mine, oracle in checks:
        e = _relerr(mine, oracle)
        worst = max(worst, e)
        print(f"      {nm:34s} rel err {e:.3e}   {'ok' if e <= KA_TF_TOL else 'FAIL'}")
        if e > KA_TF_TOL:
            _die(f"AM1a — netlist '{nm}' does not reproduce eq_reference "
                 f"({e:.3e} > {KA_TF_TOL:.0e}); the topology is mis-stamped")
    print(f"      -> {len(checks)} netlists, worst {worst:.3e}\n")

    # (b) TWO-SIDED synthetic control.  The classifier must find real where real is, AND
    #     complex where complex is -- a one-sided control cannot distinguish a correct
    #     classifier from one that says "real" unconditionally.
    lad = Net([("V", "I", 1.0),
               ("R", "I", "a", 1e3), ("C", "a", 0, 1e-7),
               ("R", "a", "b", 1e3), ("C", "b", 0, 1e-7),
               ("R", "b", "c", 1e3), ("C", "c", 0, 1e-7)], ["I", "a", "b", "c"])
    lp = lad.poles()
    floor = max(abs(p.imag) / abs(p.real) for p in lp)
    # A Butterworth Sallen-Key: R1=R2=R, C1=2*C2 -> Q = 0.7071 exactly, known complex pair.
    bq, _ = net_sk(1e3, 1e3, 2e-8, 1e-8)
    bp = bq.poles()
    q_meas = max(abs(p) / (2.0 * abs(p.real)) for p in bp)
    print(f"  (b) two-sided synthetic control:")
    print(f"      3-section RC ladder (poles KNOWN real): {len(lp)} poles, "
          f"max |Im/Re| = {floor:.3e}")
    print(f"      Butterworth SK      (pair KNOWN complex): measured Q = {q_meas:.6f} "
          f"vs exact {1/math.sqrt(2):.6f}")
    if q_meas < 0.70 or q_meas > 0.715:
        _die(f"AM1b — the classifier does not recover a KNOWN complex pair (Q {q_meas:.4f})")
    # ⭐ The bar for "is this pole complex?" is the RC ladder's own measured numerical floor,
    # taken from a network whose answer is known independently of anything being classified
    # (s113's rule), with 3 decades of margin. It is NOT a guessed number.
    tol = max(floor, 1e-12) * 1e3
    print(f"      -> |Im/Re| bar for AM2/AM3 = {tol:.3e}  (the ladder's own floor x 1000)\n")

    # (c) the Sallen-Keys' (f0, Q) from EIGENVALUES must reproduce AL5's closed form.
    # ⚠ Read from the two poles, NOT by assuming they are complex.  For s^2 + (w0/Q)s + w0^2,
    # p1*p2 = w0^2 and p1+p2 = -w0/Q whether the roots are real or complex -- so this compares
    # against AL5's closed form without presupposing the very thing being censused.  It also
    # surfaces the discriminator the biquad formalism hides: Q < 0.5 is OVERDAMPED, i.e. two
    # real poles and no resonance, however respectable "f0 and Q" look written down.
    print("  (c) Sallen-Key (f0, Q) from the pencil vs AL5's closed form `sk_params`:")
    with contextlib.redirect_stdout(io.StringIO()):
        import deficit_exponent_gate as AL   # noqa: E402  only AM1c needs it
    ok = True
    for nm, kw in (("IC4_B", AB.SK_B), ("IC4_A", AB.SK_A)):
        net, _ = net_sk(**kw)
        p = sorted(net.poles(), key=lambda z: abs(z))
        w0 = np.sqrt(p[0] * p[1])
        f0m, qm = abs(w0) / (2 * math.pi), abs(-w0 / (p[0] + p[1]))
        f0r, qr = AL.sk_params(kw["R1"], kw["R2"], kw["C1"], kw["C2"])
        d = max(abs(f0m / f0r - 1.0), abs(qm / qr - 1.0))
        ok &= d < 1e-10
        damp = "OVERDAMPED (two REAL poles)" if qr < 0.5 else "complex pair"
        print(f"      {nm}: f0 {f0m:9.2f} vs {f0r:9.2f} Hz , Q {qm:.6f} vs {qr:.6f}  "
              f"(rel {d:.1e})  -> {damp}")
    if not ok:
        _die("AM1c — the eigen-census disagrees with AL5's own closed form")
    print("      -> this instrument and AL5's agree, so AM5's grading is comparable to AL5's.")
    print("      ⭐ and it SHARPENS AL5's IC4_B row: at Q = 0.4635 that stage is overdamped, so")
    print("        it is not a mis-placed resonance — it is not a resonance at all.")
    out["am1"] = {"tf_worst_rel": worst, "n_netlists": len(checks),
                  "im_re_floor": floor, "im_re_bar": tol, "butterworth_q": q_meas}
    return tol


# ---------------------------------------------------------------------------
# AM2 -- the census
# ---------------------------------------------------------------------------
def build_all():
    """(label, position-vs-clipper, Net|None, note) in SIGNAL ORDER.

    Stages with a single capacitor are order 1, and a first-order system cannot have a complex
    pole -- so they are listed with their cap count and a `None` net rather than being built.
    The cap count is read off the shipped header, not assumed.
    """
    caps = AI.grunt_caps()
    rows = [
        ("InputBuffer C1/R2", "pre", None,
         "1 cap (InputBuffer.h: 'a single first-order high-pass')"),
        ("JFET gate C2/R4/R5", "pre", net_jfet_gate()[0], None),
    ]
    for pos in ("flat", "boost", "cut"):
        # NB this net INCLUDES the J201 drain network (ro, Rp||Cp, Rq2) -- TrebleAttack.h
        # stamps it, so the whole front end from the drain to IC2_A(+) is ONE network.
        rows.append((f"J201 drain + ladder [{pos}]", "pre", net_treble(pos)[0], None))
    for rd, lbl in ((0.0, "max gain"), (100e3, "min gain")):
        rows.append((f"DRIVE IC2_A [{lbl}]", "pre", net_drive(rd)[0], None))
    for nm, cg in caps.items():
        rows.append((f"Clipper loop [GRUNT {nm}]", "AT", net_clipper(cg, AB.CLIP_A0)[0], None))
    rows += [
        ("OdCoupling C15/(R20+R21)", "post", None,
         "1 cap (PedalChain::OdCoupling -- one node, one companion cap)"),
        ("Recovery bridged-T", "post", net_bridged_t()[0], None),
        ("Sallen-Key IC4_B", "post", net_sk(**AB.SK_B)[0], None),
        ("Sallen-Key IC4_A", "post", net_sk(**AB.SK_A)[0], None),
        ("C21 highpass", "post-BLEND", None, "1 cap (PedalChain::C21Highpass)"),
        ("EqPreGain", "post-BLEND", None, "0 caps (EqPreGain.h: 'frequency-flat, no state')"),
        ("Baxandall IC5_C [flat]", "post-BLEND", net_baxandall(0.5, 0.5)[0], None),
    ]
    for lbl, cser, ratio, rw in MID_CAPS:
        rows.append((f"MidBand [{lbl}, boost]", "post-BLEND",
                     net_mid(cser, ratio, rw, 0.9)[0], None))
    rows.append(("MasterOut C36/C37", "post-BLEND", None,
                 "2 caps, but two SEPARATE first-order sections (MasterOut.h: the wiper is "
                 "unloaded, so H factorises)"))
    return rows


def gate_am2(tol, out):
    print("\n" + "-" * 96)
    print("AM2  THE CENSUS — every stage in signal order, natural frequencies from the pencil")
    print("-" * 96)
    print("  ⚠ The census is of the chain's LINEAR structure, and that is not a gap: this pedal's")
    print("    two nonlinearities are both MEMORYLESS maps — the CD4049 VTC is memoryless in")
    print("    node W (s123, which is what let ADAA1 apply to it at all) and the J201 shaper is")
    print("    memoryless as shipped (s140/AK2, 'its incremental gain is a scalar').  A memoryless")
    print("    map has no state, so it contributes NO natural frequency; every pole in this chain")
    print("    is in a table below.\n")
    print(f"  {'stage':32s} {'pos':10s} {'ord':>3s}  {'natural frequencies (Hz)':44s} verdict")
    rows = []
    for label, pos, net, note in build_all():
        if net is None:
            print(f"  {label:32s} {pos:10s} {'<=1':>3s}  {note[:44]:44s} REAL (order)")
            rows.append({"stage": label, "position": pos, "order": 1, "poles": [],
                         "complex": False, "note": note})
            continue
        pl = classify(net.poles(), tol)
        pl.sort(key=lambda d: d["f_hz"])
        anycx = any(d["complex"] for d in pl)
        # Collapse conjugate pairs: one resonance, printed once, with its Q.
        seen, parts = set(), []
        for d in pl:
            if d["complex"]:
                key = round(d["f_hz"], 6)
                if key in seen:
                    continue
                seen.add(key)
                parts.append(f"{d['f_hz']:.4g} (Q {d['q']:.3f})")
            else:
                parts.append(f"{d['f_hz']:.4g}")
        shown = ", ".join(parts[:5])
        v = "COMPLEX PAIR" if anycx else "all real"
        print(f"  {label:32s} {pos:10s} {len(pl):3d}  {shown[:44]:44s} {v}")
        rows.append({"stage": label, "position": pos, "order": len(pl),
                     "poles": pl, "complex": bool(anycx),
                     "passive_rc": net.is_passive_rc()})
    out["am2"] = rows
    return rows


# ---------------------------------------------------------------------------
# AM3 -- the passive half, asserted rather than cited
# ---------------------------------------------------------------------------
def gate_am3(tol, out):
    print("\n" + "-" * 96)
    print("AM3  THE PASSIVE HALF — the RC theorem asserted on the shipped stamps")
    print("-" * 96)
    print("  A network of resistors and capacitors ONLY has G and C both symmetric positive")
    print("  semi-definite, so det(G + sC) = 0 has REAL non-positive roots.  Asserted here on")
    print("  the actual stamps rather than cited, with a mutation control below.\n")
    print(f"  {'stage':32s} {'sym(G)':>9s} {'sym(C)':>9s} {'min eig G':>11s} "
          f"{'min eig C':>11s} {'max|Im/Re|':>11s}")
    res = []
    for label, pos, net, note in build_all():
        if net is None or not net.is_passive_rc():
            continue
        # The node block only (the source's current row is not part of the physical network).
        k = len(net.nodes) - 1 if any(e[0] == "V" for e in net.elements) else len(net.nodes)
        G = net.G[:k, :k]
        Cm = net.Cm[:k, :k]
        sg = float(np.max(np.abs(G - G.T)))
        sc = float(np.max(np.abs(Cm - Cm.T)))
        eg = float(np.min(np.linalg.eigvalsh(0.5 * (G + G.T))))
        ec = float(np.min(np.linalg.eigvalsh(0.5 * (Cm + Cm.T))))
        pl = net.poles()
        mi = max((abs(p.imag) / abs(p.real)) for p in pl) if len(pl) else 0.0
        # PSD tolerances scale with each matrix's own norm -- an absolute bar would be a
        # guessed number against quantities spanning 1e-12 (farads) to 1e-3 (siemens).
        bad = (sg > 1e-12 * np.linalg.norm(G) or sc > 1e-12 * np.linalg.norm(Cm)
               or eg < -1e-10 * np.linalg.norm(G) or ec < -1e-10 * np.linalg.norm(Cm)
               or mi > tol)
        print(f"  {label:32s} {sg:9.1e} {sc:9.1e} {eg:11.3e} {ec:11.3e} {mi:11.3e}"
              f"{'  <-- FAIL' if bad else ''}")
        res.append({"stage": label, "sym_g": sg, "sym_c": sc, "min_eig_g": eg,
                    "min_eig_c": ec, "max_im_re": mi, "ok": not bad})
        if bad:
            _die(f"AM3 — '{label}' is stamped as passive RC but violates the theorem")

    # ⭐ Mutation control, TWO-SIDED and swept over the MECHANISM rather than over a code path.
    # The bridged-T's shunt cap C17 sits Nmid->GND.  Drive its bottom plate from a buffered
    # copy of the output instead (gain g) and the network becomes positive-feedback -- which is
    # precisely how a Sallen-Key makes a resonance out of RC parts.  g = 0 must reproduce the
    # unmutated passive stage (real), and some g > 0 must produce a complex pair; if neither
    # holds the classifier is vacuous on stages of this size.
    net, _ = net_bridged_t()
    base = [e for e in net.elements if not (e[0] == "C" and e[1] == "Nmid" and e[2] == 0)]
    print("\n  mutation control — bootstrap C17's bottom plate from the output with gain g")
    print("  (g = 0 IS the shipped passive stage; positive feedback is the resonance mechanism):")
    swept = []
    for g in (0.0, 0.5, 0.9, 1.0, 1.5):
        mut = Net(base + [("VCVS", "F", "Nout", 0, g), ("C", "Nmid", "F", AB.BT_C17)],
                  net.nodes + ["F"])
        mp = mut.poles()
        cx = any(abs(p.imag) / abs(p.real) > tol for p in mp)
        unst = any(p.real > 0 for p in mp)
        swept.append((g, bool(cx)))
        print(f"      g = {g:4.2f}  ->  {'COMPLEX pair' if cx else 'all real'}"
              f"{'  (and unstable — over-bootstrapped)' if unst else ''}")
    if swept[0][1]:
        _die("AM3 — the g = 0 arm reports COMPLEX on the shipped passive stage; the "
             "classifier fires on nothing")
    if not any(c for _, c in swept):
        _die("AM3 — no bootstrap gain produced a complex pair, so the real/complex "
             "classifier is vacuous on stages of this size")
    mcx = True
    out["am3"] = {"stages": res, "mutation_produced_complex": bool(mcx)}
    return res


# ---------------------------------------------------------------------------
# AM4 -- the clipper loop, for ALL parameter values
# ---------------------------------------------------------------------------
def gate_am4(out):
    print("\n" + "-" * 96)
    print("AM4  THE AT-CLIPPER LOOP — real-pole for ALL component values, not just the shipped")
    print("-" * 96)
    print("  The loop is the ONE active structure at or before the clipper, so 'the shipped")
    print("  values give real poles' would be too weak: a re-fit could move them.  It does not.")
    print("  With Zin = R16 + 1/(s*Cg) and Zf = R18 || 1/(s*C14), the closed loop's denominator")
    print("  is  Zf + (1+a0)*Zin , which clears to\n")
    print("      a*s^2 + b*s + c ,   a = (1+a0) R16 R18 Cg C14")
    print("                          b = (1+a0)(R16 Cg + R18 C14) + Cg R18")
    print("                          c = (1+a0)\n")
    print("  Poles are complex iff b^2 < 4ac.  But by AM-GM,")
    print("      b >= (1+a0)(R16 Cg + R18 C14) >= (1+a0)*2*sqrt(R16 Cg R18 C14)")
    print("      => b^2 >= 4 (1+a0)^2 R16 R18 Cg C14 = 4ac ,")
    print("  with equality only at R16 Cg == R18 C14 (a repeated REAL pole).  ⇒ the discriminant")
    print("  is non-negative for EVERY positive R16, R18, Cg, C14 and every a0 >= 0, and the")
    print("  extra +Cg*R18 in b only pushes it further apart.  Resonance is impossible by")
    print("  TOPOLOGY, so no re-fit of a0 or of a GRUNT cap can create one.\n")
    rng = np.random.default_rng(20260804)
    lo = 1e30
    for _ in range(AM4_TRIALS):
        r16, r18 = 10.0 ** rng.uniform(1, 7, 2)
        cg, c14 = 10.0 ** rng.uniform(-12, -5, 2)
        a0 = 10.0 ** rng.uniform(-2, 3)
        a = (1 + a0) * r16 * r18 * cg * c14
        b = (1 + a0) * (r16 * cg + r18 * c14) + cg * r18
        c = (1 + a0)
        lo = min(lo, (b * b - 4 * a * c) / (b * b))
    print(f"  random sweep, {AM4_TRIALS} draws over R in [1e1,1e7], C in [1e-12,1e-5], "
          f"a0 in [1e-2,1e3]:")
    print(f"      min normalised discriminant (b^2-4ac)/b^2 = {lo:.6f}   "
          f"{'(>= 0 everywhere)' if lo >= 0 else 'NEGATIVE — the algebra is wrong'}")
    if lo < 0:
        _die("AM4 — a random draw produced a complex pair; the AM-GM argument is mis-transcribed")
    caps = AI.grunt_caps()
    print(f"\n  shipped operating points (a0 = {AB.CLIP_A0:.4f}):")
    for nm, cg in caps.items():
        net, _ = net_clipper(cg, AB.CLIP_A0)
        pl = sorted(net.poles(), key=lambda p: abs(p))
        fs = ", ".join(f"{abs(p)/(2*math.pi):9.2f} Hz" for p in pl)
        print(f"      GRUNT {nm:5s} Cg = {cg*1e9:7.3f} nF   poles: {fs}")
    out["am4"] = {"min_norm_discriminant": lo, "trials": AM4_TRIALS,
                  "proof": "b^2 - 4ac >= 0 by AM-GM on (1+a0)(R16 Cg + R18 C14)"}
    return lo


# ---------------------------------------------------------------------------
# AM5 -- the verdict, graded against AL5's imported band
# ---------------------------------------------------------------------------
def gate_am5(rows, out, al_report=None):
    print("\n" + "-" * 96)
    print("AM5  VERDICT — every resonance found, graded against AL5's admissible bands")
    print("-" * 96)
    al_report = al_report or AL_REPORT
    if not os.path.exists(al_report):
        _die(f"AM5 — AL5's report is missing ({al_report}); the target must be IMPORTED, "
             f"never transcribed")
    al = json.load(open(al_report))["al5"]
    target, vertex = al["target"], 2934.8
    print(f"  imported from {os.path.basename(al_report)}: a carrier must reach an exponent of")
    print(f"  {target:.3f} at the vertex, at >= {al['size_frac']:.0%} of its own maximum size.\n")
    print(f"  ⚠⚠ AL5's stored `band` is a UNION over five trial Q values, so reading a "
          f"resonance\n     against min/max of it is a category error — it would report "
          f"IC4_A admissible, which\n     is the opposite of AL5's own verdict. Each "
          f"resonance is therefore graded at ITS OWN Q,\n     recomputed with AL5's own "
          f"`pair_mechanism` / `fd_exponent` so the two gates cannot drift.\n")
    with contextlib.redirect_stdout(io.StringIO()):
        import deficit_exponent_gate as AL   # noqa: E402
    wg = np.logspace(-2.5, 0.9, 20001)
    sp = 2.0 * AL.PRIMARY_HALF

    def admissible_w(q, kind):
        """AL5's own screen, at THIS resonance's Q: the w range where the mechanism both
        reaches the target exponent and delivers >= size_frac of its own maximum."""
        g = AL.pair_mechanism(wg, q, kind)
        gmax = float(np.abs(g[wg <= 1.3]).max())
        ok = [float(w) for i, w in enumerate(wg)
              if abs(g[i]) >= al["size_frac"] * gmax
              and (lambda e: e is not None and e >= target)(AL.fd_exponent(wg, g, float(w), sp))]
        return (min(ok), max(ok)) if ok else None

    found = []
    for r in rows:
        if not r.get("complex"):
            continue
        for p in r["poles"]:
            if p["complex"] and p["im"] > 0:
                found.append((r["stage"], r["position"], p["f_hz"], p["q"]))
    print(f"  {'resonance':30s} {'position':10s} {'f0 Hz':>8s} {'Q':>7s} {'w@vtx':>7s}  "
          f"admissible w at this Q          reaches?")
    hits = []
    for nm, pos, f0, q in sorted(found, key=lambda t: t[2]):
        wv = vertex / f0
        ok_any, notes = False, []
        for kind in ("Q", "f0"):
            rng = admissible_w(q, kind)
            if rng is None:
                notes.append(f"{kind}: none")
            else:
                inside = rng[0] <= wv <= rng[1]
                ok_any |= inside
                notes.append(f"{kind}: [{rng[0]:.3f},{rng[1]:.3f}]"
                             f"{' HIT' if inside else ''}")
        print(f"  {nm:30s} {pos:10s} {f0:8.1f} {q:7.4f} {wv:7.4f}  "
              f"{' ; '.join(notes):30s} {'YES' if ok_any else 'no'}")
        if ok_any:
            hits.append({"stage": nm, "position": pos, "f0": f0, "q": q, "w": wv})

    pre = [f for f in found if f[1] in ("pre", "AT")]
    print(f"\n  ⭐ resonances at or UPSTREAM of the clipper (where AF6 puts the carrier): "
          f"{len(pre)}")
    band_hits_pre = [h for h in hits if h["position"] in ("pre", "AT")]
    if pre:
        v = (f"{len(pre)} resonance(s) exist at or before the clipper — item 6's Q/damping "
             f"route has a shipped structure to act on, and the next question is size")
    else:
        v = ("NO resonance exists anywhere at or upstream of the clipper, at ANY frequency. "
             "Every stage on that side is either passive RC (real poles by the theorem, "
             "asserted in AM3) or an active stage whose loop is provably real-pole for all "
             "parameter values (AM4). So AL5's positive specification cannot be met by any "
             "structure the model contains on the side AF6 requires — item 6's carrier is "
             "either a structure the model omits, or it is not a resonance")
    print(f"\n  AM5-VERDICT: {v}")
    if hits and not band_hits_pre:
        print(f"  ⚠ {len(hits)} resonance(s) DO reach at their own Q, and every one is "
              f"POST-clipper —\n    excluded on POSITION, not on shape. A post-clipper linear "
              f"feature is pinned by\n    construction (s125), so it cannot move with drive "
              f"whatever its Q.")
    elif not hits:
        print(f"  ⚠ and NO resonance in the chain reaches the target at its own Q either — "
              f"including the\n    one that exists, which reproduces AL5's 0-of-2 rather than "
              f"contradicting it.")
    out["am5"] = {"target": target, "vertex_hz": vertex,
                  "resonances": [{"stage": a, "position": b, "f0": c, "q": d}
                                 for a, b, c, d in found],
                  "reaching": hits, "n_pre_or_at_clipper": len(pre), "verdict": v}
    return v


# ---------------------------------------------------------------------------
# AM6 -- what the model omits
# ---------------------------------------------------------------------------
def gate_am6(out):
    print("\n" + "-" * 96)
    print("AM6  WHAT THE MODEL OMITS — the positive-feedback structures that are NOT in AM2")
    print("-" * 96)
    print("  AM5's verdict is about the SHIPPED MODEL, so the honest follow-up is: which")
    print("  energy-returning structures does the real circuit have that AM2 never saw?")
    print("  circuit.md's element list has exactly one, and the shipped source has already")
    print("  sized it — quoted here rather than re-derived, so it is not left as a gap.\n")
    r9r10 = 0.5e6      # R9 || R10, circuit.md "Q2 gate": 1M || 1M
    c4 = 22e-9         # circuit.md "C4 | 22n | Q2 gate->source(output) bootstrap"
    f_boot = 1.0 / (2.0 * math.pi * r9r10 * c4)
    print(f"  * C4 (22n) bootstrapping Q2's gate to its source — the ONLY positive-feedback")
    print(f"    path at or upstream of the clipper.  Corner into R9||R10 = {r9r10/1e3:.0f}k is")
    print(f"    {f_boot:.2f} Hz, i.e. {2934.8/f_boot:.0f}x BELOW the 2935 Hz vertex, so C4 is a")
    print(f"    short across the whole audio band and the bootstrap contributes no dynamics")
    print(f"    there.  JfetStage.h models it as exactly that — a static kRq2 = 1 Mohm, with")
    print(f"    the header's own note: 'the bootstrap corner is ~14.5 Hz into R9||R10 = 500k'.")
    print(f"    ⇒ omitted as a DYNAMIC element, and its omission cannot hide a 2.5 kHz")
    print(f"    resonance: a single-pole bootstrap three decades down has none to hide.")
    # The "no inductors" half is CHECKED, not asserted: circuit.md is the project's source of
    # truth and its BOM reconciliation is explicit, so an L designator would show up in it.
    cm = open(os.path.join(os.path.dirname(HERE), ".claude", "rules", "circuit.md")).read()
    import re
    ls = sorted(set(re.findall(r"\bL\d{1,2}\b", cm)))
    ls = [x for x in ls if x not in ("L1", "L2", "L3")]      # ladder NODE names, not parts
    print(f"  * Inductors: circuit.md scanned for an L<n> designator -> "
          f"{len(ls)} found{(' ' + ', '.join(ls)) if ls else ' (its BOM reconciles R1-R54,'}")
    if not ls:
        print(f"    C1-C39, ICs, Q1/Q2, D1-D4 and no L).  With no inductor anywhere, the ONLY")
        print(f"    route to a complex pair is a controlled source — and AM2 enumerates every")
        print(f"    one the chain has.")
    else:
        _die(f"AM6 — circuit.md names inductor designators {ls}; the census's "
             f"'controlled sources are the only route to a resonance' premise does not hold")
    print(f"  ⚠ NOT claimed: that the DEVICE has no resonance there. Only that the MODEL has")
    print(f"    none, and that the one structure the model simplifies cannot be the carrier.")
    out["am6"] = {"c4_bootstrap_corner_hz": f_boot, "vertex_over_corner": 2934.8 / f_boot,
                  "inductor_designators_in_circuit_md": ls}


def main():
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--json", default=None, help="write the full census to this path")
    ap.add_argument("--al", default=None,
                    help="GATE AL's stored report (AM5's target exponent is IMPORTED from it)")
    a = ap.parse_args()

    print("=" * 96)
    print("GATE AM — THE RESONANCE CENSUS  (session 145)")
    print("  answering s141/s144's own open question: what in this chain could resonate at all?")
    print("=" * 96)

    out = {}
    tol = gate_am1(out)
    rows = gate_am2(tol, out)
    gate_am3(tol, out)
    gate_am4(out)
    v = gate_am5(rows, out, al_report=a.al)
    gate_am6(out)

    print("\n" + "=" * 96)
    print("SUMMARY")
    print("=" * 96)
    print(f"  AM5  {v}")
    print("\n  ⚠ SHAPE AND POSITION ONLY.  This gate says where a resonance could live, never")
    print("    that one is the carrier — AK5 is the standing example of a candidate passing")
    print("    every structural gate and dying on size.")

    path = a.json or OUT_JSON
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {path}")
    print("\nGATE AM: all guards passed.  AM2-AM6 are readable.")


if __name__ == "__main__":
    main()
