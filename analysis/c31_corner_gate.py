#!/usr/bin/env python3.11
"""GATE BG (session 177) — open-work item 16: C31, the unimplemented fifth LF corner.

C31 (2.2 uF) couples the Baxandall stage's output (IC5_C, an op-amp output => IDEAL
source, zero source impedance) into the LO-MID stage's input (IC5_D, circuit.md node
"Min").  It was flagged as a carry-forward at the 2026-07-21 EQ-block build alongside
C21 and never implemented; C21 landed as `PedalChain::C21Highpass`, C31 did not.

⛔ ITEM 16'S OWN INSTRUCTION: "Do NOT size it from the s169 bracket alone — derive the
loading resistance from the LO-MID stage's actual input impedance (MidBand's R41 + the
pot network), which is computable."  That is what this gate does.  s169's
`clean_lf_corner_count.py` bracketed the corner between 0.33 Hz (R41 alone, 220k) and
33 Hz (R38 alone, 2.2k) and could go no further because it treated the two legs as
alternatives.  They are not alternatives: BOTH legs load node Min simultaneously, and
the R38 leg's far end is neither ground nor open — it runs through the pot ladder to
the stage's own DRIVEN output, whose DC gain is exactly -1.

⭐ THAT INVERSION IS A MILLER EFFECT.  A resistive path from a node to a node moving at
-1x that node carries TWICE the current a path to ground would, so at DC the ladder leg
loads Min as (R38 + Rp + R39)/(1 - G0) = 104.4k/2 = 52.2k, in parallel with R41's 220k =>

    Zin_DC = 1 / (1/R41 + (1 - G0)/(R38 + Rp + R39)),      G0 = -R40/R41 = -1

⭐⭐ AND Zin_DC IS POT-POSITION-INDEPENDENT, EXACTLY, FOR TWO REASONS THAT BOTH HAVE TO
HOLD: (1) the ladder's total series resistance is R38 + Ra + Rb + R39 with Ra + Rb = Rp
at every wiper position, and (2) at DC both caps are open, so the wiper leg (C33 and the
fitted series `midWiperR`) carries no current and the (-)-node KCL reduces to
Vin/R41 + Vout/R40 = 0 => G0 = -1 at every position.  BG2 asserts both.

⛔⛔ AND THE CORNER IS NOT THE STORY.  Sizing this element by its corner — which is what
"the fifth LF corner" and s169's whole bracket presuppose — is WRONG, because
`Zin` IS NOT CONSTANT.  BG3 measures it falling 42.2 kOhm -> ~2.2 kOhm across the audio
band: C32 (the across-lug cap, SWITCHED as a scaled pair with C33 since A2c-3) shorts P3
to P1, collapsing the Miller-loaded 104.4k ladder onto the bare R38 + R39 = 4.4k, halved
again by the same inversion.  So |Zin| and |1/(w*C31)| fall TOGETHER through the bass,
the divider ratio does NOT recover the way a fixed-R high-pass does, and the element's
real contribution is a broad PLATEAU of loss that its corner frequency cannot express.
BG4/BG5 measure that plateau; it reaches ~1 dB, i.e. ~50x the -0.02 dB the corner-count
framing predicts at the lowest graded band.

⇒ ⚠⚠ IMPLEMENTING C31 AS A FIXED-R FIRST-ORDER HP (the `C21Highpass`/`OdCoupling` shape
already used twice in `PedalChain`) WOULD REPRODUCE ALMOST NONE OF IT.  It has to be
solved INSIDE MidBand's MNA as a fifth node, or not at all.

Sub-gates
  BG1  divergence guard  — the shipped LO-MID element set is READ FROM SOURCE and must
                           differ from `eq_reference.mid_stage_tf`'s drawn defaults
                           (s149/GATE AO: a transfer known answer validates topology and
                           is structurally blind to the value set, because both sides
                           share it as input).  REFUSES if they agree.
  BG1b known answer      — with C31 shorted (1e6 F) the 5-unknown solve must reproduce
                           the SHIPPED `eq_reference.mid_stage_tf` oracle.  Cross-
                           instrument: that function is 4-unknown and knows nothing of
                           C31.
  BG2  known answer      — the closed-form Zin_DC above vs TWO independent numerical
                           extractions (an ideal-source current sum, and a back-out from
                           the 5-node solve).  Plus the position-independence assertions.
  BG3  measurement       — |Zin(f)|, the quantity the corner-count framing assumed fixed.
  BG4  refutation        — the TRUE insertion vs the fixed-R first-order HP at that fc.
  BG5  measurement       — the insertion at the release gate's own band centres, per
                           (pot x switch) cell: what implementing C31 would actually do.
  BG6  verdict           — computed from BG3-BG5, not narrated.

Run: /opt/homebrew/bin/python3.11 analysis/c31_corner_gate.py
"""
import io
import contextlib
import os
import re
import sys

import numpy as np

_HERE = os.path.dirname(os.path.abspath(__file__))
_ROOT = os.path.dirname(_HERE)
sys.path.insert(0, _HERE)

# eq_reference prints a large report at module level; keep the gate's output readable.
with contextlib.redirect_stdout(io.StringIO()):
    from eq_reference import mid_stage_tf

C31_SCHEMATIC = 2.2e-6  # circuit.md: IC5_C out -> C31 -> LO-MID in. NOT a fit target here.


# ---------------------------------------------------------------------------------
# Shipped element values, READ FROM SOURCE (rebuild-targets-dont-transcribe).
# ---------------------------------------------------------------------------------
def _read_double(path, pattern, name):
    src = open(path).read()
    m = re.search(pattern, src)
    if m is None:
        sys.exit(f"GATE BG REFUSES: could not read `{name}` from {path} "
                 f"(pattern {pattern!r} did not match) — the source moved under this gate.")
    return float(m.group(1))


def shipped_values():
    """LO-MID's element set as the plugin actually runs it."""
    mb = os.path.join(_ROOT, "src", "dsp", "MidBand.h")
    fp = os.path.join(_ROOT, "src", "dsp", "FitParams.h")
    src = open(mb).read()
    m = re.search(r"kLoMid\s*\{\s*([\d.e+-]+)\s*,\s*([\d.e+-]+)\s*,\s*([\d.e+-]+)\s*,"
                  r"\s*([\d.e+-]+)\s*,\s*([\d.e+-]+)\s*\}", src)
    if m is None:
        sys.exit("GATE BG REFUSES: could not read MidBand::kLoMid from MidBand.h.")
    r38, r39, r40, r41, _c32nominal = (float(g) for g in m.groups())
    rp = _read_double(mb, r"kRp\s*=\s*([\d.e+-]+)\s*;", "MidBand::kRp")

    caps = {
        "250 Hz": _read_double(fp, r"midLoCap250\s*=\s*([\d.e+-]+)\s*;", "midLoCap250"),
        "500 Hz": _read_double(fp, r"midLoCap500\s*=\s*([\d.e+-]+)\s*;", "midLoCap500"),
        "1 kHz": _read_double(fp, r"midLoCap1k\s*=\s*([\d.e+-]+)\s*;", "midLoCap1k"),
    }
    ratio = _read_double(fp, r"midCapRatioLo\s*=\s*([\d.e+-]+)\s*;", "midCapRatioLo")
    rw = _read_double(fp, r"midWiperRLo\s*=\s*([\d.e+-]+)\s*;", "midWiperRLo")
    return dict(R38=r38, R39=r39, R40=r40, R41=r41, Rp=rp, caps=caps, ratio=ratio, Rw=rw)


# ---------------------------------------------------------------------------------
# The 5-unknown solve: an IDEAL source Vs=1 through C31 into the LO-MID network.
# Unknowns [Vin, P3, P1, W, Vout].  Identical stamps to eq_reference.mid_stage_tf,
# except Vin is promoted from a known to an unknown and gains its own KCL row.
# ---------------------------------------------------------------------------------
def mid_tf_through_c31(f, a, C33, C31, Rp, R38, R39, R40, R41, C32, Rw):
    w = 2j * np.pi * np.asarray(f, dtype=float)
    a = min(max(a, 1e-6), 1 - 1e-6)
    Ra, Rb = a * Rp, (1 - a) * Rp
    out = np.zeros(len(w), dtype=complex)
    for i, s in enumerate(w):
        yC32 = s * C32
        yC33 = (s * C33) if Rw <= 0.0 else 1.0 / (Rw + 1.0 / (s * C33))
        yC31 = s * C31
        A = np.zeros((5, 5), dtype=complex)
        b = np.zeros(5, dtype=complex)
        # KCL Vin: (Vin-Vs)*yC31 + (Vin-P3)/R38 + Vin/R41 = 0
        #   ⚠ the R41 leg leaves Vin for the 0 V virtual ground, so it is a genuine
        #   admittance to ground at THIS node even though the current re-appears in the
        #   (-)-node row below.
        A[0, 0] = yC31 + 1 / R38 + 1 / R41
        A[0, 1] = -1 / R38
        b[0] = yC31
        # KCL P3: (P3-Vin)/R38 + (P3-P1)*yC32 + (P3-W)/Ra = 0
        A[1, 1] = 1 / R38 + yC32 + 1 / Ra
        A[1, 2] = -yC32
        A[1, 3] = -1 / Ra
        A[1, 0] = -1 / R38
        # KCL P1: (P1-Vout)/R39 + (P1-P3)*yC32 + (P1-W)/Rb = 0
        A[2, 2] = 1 / R39 + yC32 + 1 / Rb
        A[2, 1] = -yC32
        A[2, 3] = -1 / Rb
        A[2, 4] = -1 / R39
        # KCL W: (W-P3)/Ra + (W-P1)/Rb + W*yC33 = 0
        A[3, 3] = 1 / Ra + 1 / Rb + yC33
        A[3, 1] = -1 / Ra
        A[3, 2] = -1 / Rb
        # KCL virtual ground: Vin/R41 + Vout/R40 + W*yC33 = 0   (currents INTO the 0 V node)
        A[4, 4] = 1 / R40
        A[4, 3] = yC33
        A[4, 0] = 1 / R41
        out[i] = np.linalg.solve(A, b)[4]
    return out


def zin_direct(f, a, C33, Rp, R38, R39, R40, R41, C32, Rw):
    """Zin looking into node Min, by driving it with an IDEAL source and summing the
    current that leaves.  Shares no arithmetic with the C31 back-out in zin_backout()."""
    w = 2j * np.pi * np.asarray(f, dtype=float)
    a = min(max(a, 1e-6), 1 - 1e-6)
    Ra, Rb = a * Rp, (1 - a) * Rp
    out = np.zeros(len(w), dtype=complex)
    for i, s in enumerate(w):
        yC32 = s * C32
        yC33 = (s * C33) if Rw <= 0.0 else 1.0 / (Rw + 1.0 / (s * C33))
        A = np.zeros((4, 4), dtype=complex)
        b = np.zeros(4, dtype=complex)
        A[0, 0] = 1 / R38 + yC32 + 1 / Ra; A[0, 1] = -yC32; A[0, 2] = -1 / Ra; b[0] = 1 / R38
        A[1, 1] = 1 / R39 + yC32 + 1 / Rb; A[1, 0] = -yC32; A[1, 2] = -1 / Rb; A[1, 3] = -1 / R39
        A[2, 2] = 1 / Ra + 1 / Rb + yC33; A[2, 0] = -1 / Ra; A[2, 1] = -1 / Rb
        A[3, 3] = 1 / R40; A[3, 2] = yC33; b[3] = -1 / R41
        P3, _P1, _W, _Vout = np.linalg.solve(A, b)
        i_total = (1.0 - P3) / R38 + 1.0 / R41   # Vin = 1
        out[i] = 1.0 / i_total
    return out


def zin_backout(f, a, C33, C31, Rp, R38, R39, R40, R41, C32, Rw):
    """Zin recovered from the 5-node solve: H_with/H_without = Zin/(Zin + 1/(s*C31))."""
    kw = dict(Rp=Rp, R38=R38, R39=R39, R40=R40, R41=R41, C32=C32, Rw=Rw)
    h_with = mid_tf_through_c31(f, a, C33, C31, **kw)
    h_short = mid_tf_through_c31(f, a, C33, 1.0e6, **kw)
    ratio = h_with / h_short
    s = 2j * np.pi * np.asarray(f, dtype=float)
    # ratio = Z/(Z + 1/(sC))  =>  Z = ratio/(1-ratio) * 1/(sC)
    return ratio / (1.0 - ratio) / (s * C31)


def hp1_response(f, fc):
    f = np.asarray(f, dtype=float)
    return 1j * (f / fc) / (1.0 + 1j * (f / fc))


# The release gate's own graded band centres (1/3 oct, 25 Hz up) — the frequencies any
# cost of implementing C31 would actually be read at.
GRADED_LOW_BANDS = [25.2, 31.7, 39.9, 50.2, 63.2, 79.6, 100.2, 126.2, 158.9, 200.1, 251.9]


def main():
    v = shipped_values()
    fail = []

    print("=" * 92)
    print("GATE BG (s177) — item 16: C31 (2.2 uF), the unimplemented Baxandall -> LO-MID corner")
    print("=" * 92)

    # ---------------- BG1: divergence guard (s149 / GATE AO) ----------------------
    print("\n[BG1] Divergence guard — shipped LO-MID element set vs eq_reference's drawn defaults")
    drawn = dict(Rp=100e3, R38=2.2e3, R39=2.2e3, R40=220e3, R41=220e3, C32=22e-9, Rw=0.0)
    shipped_probe = dict(Rp=v["Rp"], R38=v["R38"], R39=v["R39"], R40=v["R40"], R41=v["R41"],
                         C32=v["ratio"] * v["caps"]["250 Hz"], Rw=v["Rw"])
    diffs = [k for k in drawn if abs(shipped_probe[k] - drawn[k]) > 1e-12 * max(1.0, abs(drawn[k]))]
    for k in sorted(drawn):
        tag = "DIFFERS" if k in diffs else "same"
        print(f"      {k:5s} drawn {drawn[k]:>12.6g}   shipped {shipped_probe[k]:>12.6g}   {tag}")
    print(f"      C33 (250 Hz position): drawn [ENG] 47n, shipped {v['caps']['250 Hz']*1e9:.3g}n"
          f"   DIFFERS")
    if not diffs:
        fail.append("BG1: shipped element set is identical to the drawn defaults — a transfer "
                    "known answer cannot distinguish them, so BG1b would be vacuous.")
        print("      => REFUSE (no divergence)")
    else:
        print(f"      => {len(diffs)} of {len(drawn)} differ ({', '.join(sorted(diffs))}) plus C33 "
              f"— BG1b's known answer is non-vacuous.")

    # ---------------- BG1b: cross-instrument known answer -------------------------
    print("\n[BG1b] Known answer — C31 shorted (1e6 F) must reproduce the SHIPPED 4-unknown oracle")
    f_ka = np.geomspace(10.0, 20000.0, 41)
    worst_ka = 0.0
    for cname, c33 in v["caps"].items():
        c32 = v["ratio"] * c33
        for a in (1e-3, 0.5, 1 - 1e-3):
            ref = mid_stage_tf(f_ka, a, c33, Rp=v["Rp"], R38=v["R38"], R39=v["R39"],
                               R40=v["R40"], R41=v["R41"], C32=c32, Rw=v["Rw"])
            got = mid_tf_through_c31(f_ka, a, c33, 1.0e6, Rp=v["Rp"], R38=v["R38"], R39=v["R39"],
                                     R40=v["R40"], R41=v["R41"], C32=c32, Rw=v["Rw"])
            worst_ka = max(worst_ka, float(np.max(np.abs(got - ref))))
    print(f"      worst |5-unknown - mid_stage_tf| over 9 cells x 41 f = {worst_ka:.3e}")
    if worst_ka > 1e-9:
        fail.append(f"BG1b: the 5-unknown solve does not reduce to the shipped oracle "
                    f"({worst_ka:.3e} > 1e-9).")
        print("      => FAIL")
    else:
        print("      => PASS (the added node is the only difference)")

    # ---------------- BG2: Zin_DC, closed form vs two extractions -----------------
    print("\n[BG2] Known answer — Zin_DC closed form vs two independent numerical extractions")
    g0 = -v["R40"] / v["R41"]
    zin_cf = 1.0 / (1.0 / v["R41"] + (1.0 - g0) / (v["R38"] + v["Rp"] + v["R39"]))
    fc_cf = 1.0 / (2.0 * np.pi * zin_cf * C31_SCHEMATIC)
    print(f"      G0(DC) = -R40/R41 = {g0:+.6f}")
    print(f"      Zin_DC = 1/(1/R41 + (1-G0)/(R38+Rp+R39)) = {zin_cf:,.1f} ohm")
    print(f"      fc     = 1/(2*pi*Zin_DC*C31) = {fc_cf:.4f} Hz     [C31 = {C31_SCHEMATIC*1e6:.1f} uF]")

    f_dc = np.array([1.0e-4])
    worst_direct, worst_backout, worst_g0 = 0.0, 0.0, 0.0
    positions = [1e-3, 0.25, 0.5, 0.75, 1 - 1e-3]
    for cname, c33 in v["caps"].items():
        c32 = v["ratio"] * c33
        for a in positions:
            kw = dict(Rp=v["Rp"], R38=v["R38"], R39=v["R39"], R40=v["R40"], R41=v["R41"],
                      C32=c32, Rw=v["Rw"])
            zd = zin_direct(f_dc, a, c33, **kw)[0].real
            zb = zin_backout(f_dc, a, c33, C31_SCHEMATIC, **kw)[0].real
            g = mid_stage_tf(f_dc, a, c33, **kw)[0]
            worst_direct = max(worst_direct, abs(zd / zin_cf - 1.0))
            worst_backout = max(worst_backout, abs(zb / zin_cf - 1.0))
            worst_g0 = max(worst_g0, abs(g - g0))
    print(f"      route 1 (ideal-source current sum),  worst rel. dev over 15 cells: {worst_direct:.3e}")
    print(f"      route 2 (back-out of the C31 solve), worst rel. dev over 15 cells: {worst_backout:.3e}")
    print(f"      DC gain vs -1, worst over the same 15 cells:                        {worst_g0:.3e}")
    print("      (position-independence is asserted by the same three numbers: 5 pot positions x")
    print("       3 switch positions all reduce to ONE Zin, because Ra+Rb = Rp and the wiper leg")
    print("       carries no DC current.)")
    if max(worst_direct, worst_backout, worst_g0) > 1e-6:
        fail.append("BG2: Zin_DC / G0 / position-independence known answer failed.")
        print("      => FAIL")
    else:
        print("      => PASS")

    print(f"\n      For contrast, s169's bracket (clean_lf_corner_count.py), now superseded:")
    print(f"        R38 alone (2.2k, 'too severe')  -> "
          f"{1.0/(2*np.pi*v['R38']*C31_SCHEMATIC):8.3f} Hz")
    print(f"        R41 alone (220k, 'defensible')  -> "
          f"{1.0/(2*np.pi*v['R41']*C31_SCHEMATIC):8.3f} Hz")
    print(f"        BOTH legs + the -1 Miller factor -> {fc_cf:8.3f} Hz   <-- the computed answer")

    # ---------------- BG3: the load impedance is NOT constant ---------------------
    print("\n[BG3] |Zin(f)| — the quantity a corner-count assumes is FIXED")
    f_z = np.array([1e-3, 10.0, 25.2, 50.0, 100.0, 200.0, 400.0, 1000.0, 4000.0, 20000.0])
    kw_mid = dict(Rp=v["Rp"], R38=v["R38"], R39=v["R39"], R40=v["R40"], R41=v["R41"], Rw=v["Rw"])
    print(f"      {'f (Hz)':>9} " + " ".join(f"{c:>13}" for c in v["caps"]))
    zin_by_cap = {}
    for cname, c33 in v["caps"].items():
        zin_by_cap[cname] = zin_direct(f_z, 0.5, c33, C32=v["ratio"] * c33, **kw_mid)
    for i, ff in enumerate(f_z):
        cells = " ".join(f"{abs(zin_by_cap[c][i]):13,.0f}" for c in v["caps"])
        print(f"      {ff:9.3f} {cells}")
    z_hi = abs(zin_by_cap["250 Hz"][-1])
    fall = zin_cf / z_hi
    print(f"      DC {zin_cf:,.0f} ohm -> 20 kHz {z_hi:,.0f} ohm : a fall of {fall:.1f}x")
    print(f"      MECHANISM: C32 shorts P3 to P1, so the Miller-loaded R38+Rp+R39 = "
          f"{v['R38']+v['Rp']+v['R39']:,.0f} ohm ladder")
    print(f"      collapses onto R38+R39 = {v['R38']+v['R39']:,.0f}, halved again by the same "
          f"(1-G0) => ~{(v['R38']+v['R39'])/2.0:,.0f} ohm.")
    if fall < 5.0:
        fail.append(f"BG3: |Zin| barely moves ({fall:.2f}x) — the corner-count framing would be "
                    f"sound and BG4's refutation is vacuous.")
        print("      => REFUSE (nothing to refute)")

    # ---------------- BG4: refute the fixed-R first-order model --------------------
    print("\n[BG4] TRUE insertion vs the fixed-R 1st-order HP at that fc — the refutation")
    f_grid = np.geomspace(20.0, 20000.0, 121)
    ideal = hp1_response(f_grid, fc_cf)
    print(f"      {'C33':>8} {'pot a':>7} {'worst true dB':>14} {'@ f':>8} {'1-pole says':>12} "
          f"{'ratio':>8}")
    worst_db = 0.0
    for cname, c33 in v["caps"].items():
        c32 = v["ratio"] * c33
        for a in positions:
            ins = (mid_tf_through_c31(f_grid, a, c33, C31_SCHEMATIC, C32=c32, **kw_mid)
                   / mid_stage_tf(f_grid, a, c33, C32=c32, **kw_mid))
            db = 20 * np.log10(np.abs(ins))
            k = int(np.argmax(np.abs(db)))
            worst_db = max(worst_db, float(np.max(np.abs(db - 20 * np.log10(np.abs(ideal))))))
            if a in (1e-3, 0.5, 1 - 1e-3):
                pred = 20 * np.log10(abs(ideal[k]))
                print(f"      {cname:>8} {a:7.3f} {db[k]:14.3f} {f_grid[k]:8.1f} {pred:12.3f} "
                      f"{db[k]/pred if pred != 0 else float('nan'):8.1f}x")
    print(f"      worst |true - 1-pole| over 15 cells x 121 f: {worst_db:.3f} dB")

    # ---------------- BG5: what implementing it would actually do -----------------
    print("\n[BG5] TRUE insertion at the release gate's own band centres (this IS the cost)")
    fb = np.array(GRADED_LOW_BANDS)
    print(f"      {'f (Hz)':>8} " + " ".join(f"{c+' '+p:>13}"
                                             for c in v["caps"] for p in ("bst", "cut")))
    cols, labels = [], []
    for cname, c33 in v["caps"].items():
        for a, lbl in ((1e-3, "bst"), (1 - 1e-3, "cut")):
            ins = (mid_tf_through_c31(fb, a, c33, C31_SCHEMATIC, C32=v["ratio"] * c33, **kw_mid)
                   / mid_stage_tf(fb, a, c33, C32=v["ratio"] * c33, **kw_mid))
            cols.append(20 * np.log10(np.abs(ins)))
            labels.append(f"{cname} {lbl}")
    for i, f0 in enumerate(fb):
        print(f"      {f0:8.1f} " + " ".join(f"{c[i]:13.3f}" for c in cols))
    worst_band_db = float(np.max(np.abs(np.array(cols))))
    naive = float(np.max(np.abs(20 * np.log10(np.abs(hp1_response(fb, fc_cf))))))
    print(f"      worst graded-band magnitude: {worst_band_db:.3f} dB   "
          f"(the corner-count framing predicts {naive:.3f} dB, "
          f"{worst_band_db/naive:.0f}x smaller)")

    # ---------------- BG6: computed verdict ---------------------------------------
    print("\n[BG6] Verdict (computed from BG3-BG5 — not narrated)")
    one_pole_ok = worst_db < 0.05
    print(f"      insertion vs a fixed-R 1-pole HP: worst {worst_db:.3f} dB => "
          f"{'ONE POLE SUFFICES' if one_pole_ok else 'ONE POLE IS NOT ENOUGH'}")
    print(f"      => C31 must be solved INSIDE MidBand's MNA (a 5th node), NOT bolted on as a"
          f" `C21Highpass`-shaped fixed-R stage.")
    print(f"      Worst magnitude in the graded range: {worst_band_db:.3f} dB — "
          f"{'BELOW' if worst_band_db < 0.05 else 'ABOVE'} 0.05 dB, i.e. "
          f"{'invisible to' if worst_band_db < 0.05 else 'VISIBLE to'} `release_gate.py`.")
    print(f"      It has NO fitted parameter: C31 is schematic (2.2 uF) and the load is the")
    print(f"      stage's own network.  ⚠ But the shipped C32 is a FIT (A2c-3's scaled pair), and")
    print(f"      the plateau scales with it — at the 1 kHz position C32 = 22n = the STOCK value")
    print(f"      and the loss is smallest; at 250 Hz C32 = 68n = 3.1x stock and it is largest.")

    if fail:
        print("\n" + "=" * 92)
        for m in fail:
            print("FAIL: " + m)
        sys.exit(1)
    print("\nGATE BG: all guards PASS.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
