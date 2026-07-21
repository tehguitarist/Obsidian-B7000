#!/usr/bin/env python3
"""Filter-sim sanity checks for Obsidian-B7000 (open item c).

All stages simulated from the schematic-VERIFIED node graphs (2026-07-19 tone-stack redraw):

MID stage (LO-MID IC5_D / HI-MID IC6_A), signal ground = VD = 0:
  Vin --R41--> (-)=0 ; (-) --R40--> Vout            (flat inverting-unity path)
  Vin --R38--> P3 ; P1 --R39--> Vout                (pot end legs)
  pot Rp between P3..W..P1 (position a = fraction of Rp between P3 and W)
  C32 across P3-P1 ; W --C33--> (-)=0               (C33 = switchable series cap)

BAXANDALL (IC5_C):
  Vin --R33--> A ; B --R34--> Vout ; bass pot A..Wb..B ; C25 A-Wb ; C26 Wb-B ; Wb --R35--> (-)
  Vin --C28--> T3 ; T1 --C29--> Vout ; treble pot T3..Wt..T1 ; Wt --R36--> (-)
  feedback (-) --R37||C30--> Vout
"""
import numpy as np

def treble_attack_tf(f, position, R7=200e3, R8=470e3, R11=470e3, R12=6.8e3, R14=22e3, R13=1e6,
                     C5=22e-9, C9=22e-9, C6=22e-9, C7=100e-9, C8=220e-12):
    """TrebleAttack stage (circuit.md "Treble network + ATTACK", node graph VERIFIED 2026-07-19).

    Convention (build-plan Phase 4, user-confirmed 2026-07-20): the J201 drain (node G) is an
    IDEAL voltage source (source Z = 0) — revisit with an explicit Rout at Phase 7 capture.
    Stage output = V(Q) = the voltage presented to IC2_A(+); the DRIVE stage multiplies it.
    IC2_A(+) draws no current, so V(Q) is a clean stage boundary.

    Nodes (signal ground = VD = 0):
      G(=Vin) --R7--> M --R8--> P                          (top rail; M = R7/R8 junction)
      G --C5--> L1 --C9--> L2 --C6--> M                     (lower series-cap ladder; L3 = M)
      L1 --R12--> GND ;  L2 --R14--> GND                    (ladder shunts)
      P --R11--> GND ;  P --C7--> Q ;  Q --R13--> GND       (coupling into IC2_A(+))
    ATTACK position (UI top->bottom = Flat/Boost/Cut). The switch POLE is C8's
    bottom plate (C8 top is permanently on P); the two throws are M and GND —
    node M is NEVER grounded, so the forward path is intact in every position
    (schematic-verified 2026-07-20, corrects the earlier "Cut = M->GND" error):
      'flat'  : pole open        -> C8 inactive; base network only
      'boost' : pole -> M        -> C8 bridges R8 (M<->P): HF bypass -> treble boost
      'cut'   : pole -> GND      -> C8 (220pF) shunts P to GND: HF rolloff -> treble cut
    """
    w = 2j * np.pi * f
    out = np.zeros(len(f), dtype=complex)
    pos = position.lower()
    for i, s in enumerate(w):
        yC5, yC9, yC6, yC7, yC8 = s * C5, s * C9, s * C6, s * C7, s * C8
        Vin = 1.0
        # Unknowns: [M, P, L1, L2, Q]. Forward path M->R8->P intact in all positions.
        # Boost: C8 couples M<->P. Cut: C8 shunts P->GND. Flat: C8 absent.
        gMP = yC8 if pos == 'boost' else 0.0   # C8 as R8 bridge
        gPg = yC8 if pos == 'cut' else 0.0     # C8 as shunt at P
        A = np.zeros((5, 5), dtype=complex); b = np.zeros(5, dtype=complex)
        # M: (M-Vin)/R7 + (M-P)/R8 + (M-L2)*yC6 + (M-P)*gMP = 0
        A[0, 0] = 1 / R7 + 1 / R8 + yC6 + gMP; A[0, 1] = -(1 / R8 + gMP); A[0, 3] = -yC6
        b[0] = Vin / R7
        # P: (P-M)/R8 + P/R11 + (P-Q)*yC7 + (P-M)*gMP + P*gPg = 0
        A[1, 1] = 1 / R8 + 1 / R11 + yC7 + gMP + gPg; A[1, 0] = -(1 / R8 + gMP); A[1, 4] = -yC7
        # L1: (L1-Vin)*yC5 + (L1-L2)*yC9 + L1/R12 = 0
        A[2, 2] = yC5 + yC9 + 1 / R12; A[2, 3] = -yC9; b[2] = yC5 * Vin
        # L2: (L2-L1)*yC9 + (L2-M)*yC6 + L2/R14 = 0
        A[3, 3] = yC9 + yC6 + 1 / R14; A[3, 2] = -yC9; A[3, 0] = -yC6
        # Q: (Q-P)*yC7 + Q/R13 = 0
        A[4, 4] = yC7 + 1 / R13; A[4, 1] = -yC7
        x = np.linalg.solve(A, b)
        out[i] = x[4]
    return out

def drive_stage_tf(f, Rdrive, R15=330e3, C10=47e-12, R17=3.3e3, R32=1e3):
    """DRIVE stage (IC2_A) — circuit.md "DRIVE gain stage (IC2_A)".

    Non-inverting op-amp gain stage. Signal enters IC2_A(+) as V(Q) (the TrebleAttack
    output); the (-) node sits at V(+) for an ideal op-amp and draws no current, so the
    stage decomposes (dsp.md "ideal op-amp decomposition") into:
        gain-set leg Zg  = R17 + Rdrive + R32   (- node -> AC ground/VD; purely resistive)
        feedback leg Zf  = R15 || C10           (- node -> output)
        Vout = Vin * (1 + Zf/Zg)                (non-inverting)
      Zf(s) = R15 / (1 + s*R15*C10)   -> only frequency-dependence is the C10 HF rolloff
                                          of the feedback impedance (corner ~10.3 kHz).

    Rdrive = the DRIVE rheostat's electrical resistance (0 .. 100k). The knob->Rdrive
    taper (C-taper, knob up = LESS R = MORE gain) is a SEPARATE concern validated apart
    from FR — this oracle takes the electrical value directly so the C++ FR test can drive
    matched Rdrive values (same decoupling as the TrebleAttack test's fixed values).

    DC gain check: Rdrive=100k -> 1+330k/104.3k = 4.16x (min); Rdrive=0 -> 1+330k/4.3k
    = 77.7x (max) — matches circuit.md's "~4x .. ~78x".
    """
    w = 2j * np.pi * f
    Zg = R17 + Rdrive + R32
    Zf = R15 / (1.0 + w * R15 * C10)
    return 1.0 + Zf / Zg


def mid_stage_tf(f, a, C33, Rp=100e3, R38=2.2e3, R39=2.2e3, R40=220e3, R41=220e3, C32=22e-9):
    """Return complex gain Vout/Vin of the mid peaking stage at frequencies f, pot position a."""
    w = 2j * np.pi * f
    a = min(max(a, 1e-6), 1 - 1e-6)
    Ra, Rb = a * Rp, (1 - a) * Rp
    out = np.zeros(len(f), dtype=complex)
    for i, s in enumerate(w):
        yC32, yC33 = s * C32, s * C33
        # unknowns x = [P3, P1, W, Vout]; Vin = 1; virtual ground node = 0 V (ideal op-amp)
        A = np.zeros((4, 4), dtype=complex); b = np.zeros(4, dtype=complex)
        # KCL P3: (P3-Vin)/R38 + (P3-P1)*yC32 + (P3-W)/Ra = 0
        A[0, 0] = 1 / R38 + yC32 + 1 / Ra; A[0, 1] = -yC32; A[0, 2] = -1 / Ra; b[0] = 1 / R38
        # KCL P1: (P1-Vout)/R39 + (P1-P3)*yC32 + (P1-W)/Rb = 0
        A[1, 1] = 1 / R39 + yC32 + 1 / Rb; A[1, 0] = -yC32; A[1, 2] = -1 / Rb; A[1, 3] = -1 / R39
        # KCL W: (W-P3)/Ra + (W-P1)/Rb + W*yC33 = 0
        A[2, 2] = 1 / Ra + 1 / Rb + yC33; A[2, 0] = -1 / Ra; A[2, 1] = -1 / Rb
        # KCL at virtual ground: Vin/R41 + Vout/R40 + W*yC33 = 0  (currents INTO the 0V node)
        A[3, 3] = 1 / R40; A[3, 2] = yC33; b[3] = -1 / R41
        x = np.linalg.solve(A, b)
        out[i] = x[3]
    return out

def baxandall_tf(f, ab, at, Rp=100e3, R33=10e3, R34=10e3, R35=10e3, R36=3.3e3,
                 C25=22e-9, C26=22e-9, C28=10e-9, C29=10e-9, R37=1e6, C30=47e-12):
    w = 2j * np.pi * f
    ab = min(max(ab, 1e-6), 1 - 1e-6); at = min(max(at, 1e-6), 1 - 1e-6)
    Rba, Rbb = ab * Rp, (1 - ab) * Rp
    Rta, Rtb = at * Rp, (1 - at) * Rp
    out = np.zeros(len(f), dtype=complex)
    for i, s in enumerate(w):
        y25, y26, y28, y29, y30 = s * C25, s * C26, s * C28, s * C29, s * C30
        # unknowns: [A, B, Wb, T3, T1, Wt, Vout]
        M = np.zeros((7, 7), dtype=complex); b = np.zeros(7, dtype=complex)
        # A: (A-1)/R33 + (A-Wb)*y25 + (A-Wb)/Rba = 0   (pot upper half A->Wb, C25 A->Wb)
        M[0, 0] = 1 / R33 + y25 + 1 / Rba; M[0, 2] = -(y25 + 1 / Rba); b[0] = 1 / R33
        # B: (B-Vout)/R34 + (B-Wb)*y26 + (B-Wb)/Rbb = 0
        M[1, 1] = 1 / R34 + y26 + 1 / Rbb; M[1, 2] = -(y26 + 1 / Rbb); M[1, 6] = -1 / R34
        # Wb: (Wb-A)(y25+1/Rba) + (Wb-B)(y26+1/Rbb) + Wb/R35 = 0
        M[2, 2] = y25 + 1 / Rba + y26 + 1 / Rbb + 1 / R35
        M[2, 0] = -(y25 + 1 / Rba); M[2, 1] = -(y26 + 1 / Rbb)
        # T3: (T3-1)*y28 + (T3-Wt)/Rta = 0
        M[3, 3] = y28 + 1 / Rta; M[3, 5] = -1 / Rta; b[3] = y28
        # T1: (T1-Vout)*y29 + (T1-Wt)/Rtb = 0
        M[4, 4] = y29 + 1 / Rtb; M[4, 5] = -1 / Rtb; M[4, 6] = -y29
        # Wt: (Wt-T3)/Rta + (Wt-T1)/Rtb + Wt/R36 = 0
        M[5, 5] = 1 / Rta + 1 / Rtb + 1 / R36; M[5, 3] = -1 / Rta; M[5, 4] = -1 / Rtb
        # virtual ground: Wb/R35 + Wt/R36 + Vout*(1/R37 + y30) = 0
        M[6, 2] = 1 / R35; M[6, 5] = 1 / R36; M[6, 6] = 1 / R37 + y30
        x = np.linalg.solve(M, b)
        out[i] = x[6]
    return out

def bridged_t_tf(f, R22=100e3, R23=33e3, C16=680e-12, C17=22e-9, Rload=None):
    """buf-out --C16--> Nout ; buf-out --R22--> Nmid --R23--> Nout ; Nmid --C17--> GND.

    Rload=None (default) = UNLOADED — the documented ~717 Hz/−28 dB numbers, and a fair
    approximation: the real load is R24(10k) + the IC4_B SK's input impedance, which is
    bootstrapped high in the SK passband (output ≈ input at 717 Hz << 10.7 kHz corner).
    Pass a resistance to sensitivity-check loading; the WDF stage includes the real load,
    so expect small notch-region deviations vs this unloaded oracle (build-plan Phase 4)."""
    w = 2j * np.pi * f
    out = np.zeros(len(f), dtype=complex)
    for i, s in enumerate(w):
        y16, y17 = s * C16, s * C17
        # unknowns [Nmid, Nout]; Vin = 1 (ideal buffer out)
        M = np.zeros((2, 2), dtype=complex); b = np.zeros(2, dtype=complex)
        M[0, 0] = 1 / R22 + 1 / R23 + y17; M[0, 1] = -1 / R23; b[0] = 1 / R22
        M[1, 1] = 1 / R23 + y16 + (0 if Rload is None else 1 / Rload); M[1, 0] = -1 / R23; b[1] = y16
        # unloaded (SK input is high-Z through R24 into unity SK ~ follows), good first approx
        x = np.linalg.solve(M, b)
        out[i] = x[1]
    return out

def sallen_key_lpf_tf(f, R1, R2, C1, C2):
    """Unity-gain (voltage-follower) 2nd-order Sallen-Key LOW-PASS (IC4_B, IC4_A).

    Topology (circuit.md "Recovery + bandlimiting", IC4_B/IC4_A rows):
        Vin --R1--> X --R2--> Y(=op-amp + input) ;  Y --C2--> GND
        C1 from X to Vout ;  op-amp = unity follower so Vout = V(Y)
    C1 = the FEEDBACK cap (mid-node X -> output), C2 = the to-GND cap at the + input.

    Derived by the SAME 2-node nodal formulation the C++ MNA stage implements
    (unknowns X, Y; the op-amp OUTPUT node O = Y is DRIVEN, so C1's current at
    node X couples to Y via O=Y but injects NOTHING into node Y's KCL — the
    asymmetry that makes an active SK non-reciprocal). Closed form:
        H(s) = 1 / (1 + s*C2*(R1+R2) + s^2 * R1*R2*C1*C2)
    -> w0 = 1/sqrt(R1 R2 C1 C2) ; both w0 and the damping term C2*(R1+R2) are
    symmetric in R1<->R2 (so R1-vs-R2 assignment is irrelevant), but Q depends
    on C2 ALONE in the s-term, so the C1(feedback)/C2(GND) assignment matters.

    IC4_B: R1=10k(R24) R2=22k(R25) C1=1n(C18) C2=1n(C27)   -> fc ~ 10.7 kHz
    IC4_A: R1=22k(R26) R2=47k(R27) C1=2n2(C19) C2=1n(C20)  -> fc ~ 3.3 kHz
    """
    s = 2j * np.pi * f
    return 1.0 / (1.0 + s * C2 * (R1 + R2) + s * s * R1 * R2 * C1 * C2)

def level_blend_tf(level, blend, vo=1.0, vc=0.0, p=1.43):
    """LEVEL (VR2) + BLEND (VR1) — loaded resistive network, DC transfer.

    A 1-node KCL solve for the loaded LEVEL/BLEND pot pair (see LevelBlend.h
    for full circuit topology). Returns Vout for a given OD (vo) and clean (vc)
    input, with the LEVEL taper exponent p (power law: L = level^p).

    At Phase 7, p is fit to the blend-0700/1200 captures; this default matches
    kLevelTaperExp = 1.43 in the C++ stage (dsp.md §tapers recommended start).

    Referenced by tests/LevelBlendTest.cpp as the analytic oracle.
    """
    # LEVEL taper (power law).
    L = 0.0 if level <= 0.0 else (1.0 if level >= 1.0 else level ** p)
    B = np.clip(blend, 0.0, 1.0)  # B-taper = linear

    # LEVEL wiper voltage (loaded by the 100k BLEND pot).
    if L <= 0.0:
        vw = 0.0
    elif L >= 1.0:
        vw = vo
    else:
        invRup = 1.0 / (1.0 - L)
        invRdn = 1.0 / L
        invTotal = invRup + invRdn + 1.0
        vw = (vo * invRup + vc) / invTotal

    # BLEND wiper = linear crossfade.
    return (1.0 - B) * vc + B * vw


f = np.logspace(np.log10(10), np.log10(20000), 1200)

print("=" * 72)
print("MID STAGES — peak centre & gain vs C33/C35 (pot full boost a=0 -> check!)")
print("=" * 72)
# which pot extreme is boost? try both ends; magnitude peak
# NB: the across-lug cap differs per band — LO-MID C32=22n (the mid_stage_tf
# default) but HI-MID C34=6n8 — so HI-MID rows MUST override C32=6.8e-9, else
# the printed peak centres are wrong (~405 vs the correct 728 Hz for 15n). With
# C34=6n8 the HI-MID peaks land at 728/1552/3116 Hz, matching circuit.md's table.
for band, caps, targets, cAcross in [
    ("LO-MID (C33)", [("47n", 47e-9, 250), ("22n STOCK-board", 22e-9, None), ("10n", 10e-9, 500), ("2n2", 2.2e-9, 1000)], None, 22e-9),
    ("HI-MID (C35)", [("15n", 15e-9, 750), ("3n3", 3.3e-9, 1500), ("820p", 820e-12, 3000), ("680p STOCK-board", 680e-12, None)], None, 6.8e-9),
]:
    for name, C, tgt in caps:
        g_end0 = mid_stage_tf(f, 0.0, C, C32=cAcross)
        g_end1 = mid_stage_tf(f, 1.0, C, C32=cAcross)
        g_mid = mid_stage_tf(f, 0.5, C, C32=cAcross)
        db0, db1, dbm = (20 * np.log10(np.abs(g)) for g in (g_end0, g_end1, g_mid))
        i0, i1 = np.argmax(db0), np.argmax(db1)
        # boost end = whichever end yields > flat gain peak
        if db0[i0] >= db1[np.argmax(db1)]:
            fb, gb = f[i0], db0[i0]; cut = db1; end = "a=0 (wiper at P3/input side)"
        else:
            fb, gb = f[i1], db1[i1]; cut = db0; end = "a=1 (wiper at P1/output side)"
        ic = np.argmin(cut)
        tgt_s = f"target {tgt} Hz -> err {100*(fb-tgt)/tgt:+.1f}%" if tgt else "reference (no target)"
        print(f"{band} {name:>16}: boost peak {fb:7.1f} Hz {gb:+5.2f} dB | cut dip {f[ic]:7.1f} Hz {cut[ic]:+6.2f} dB | flat@centre {dbm[np.argmax(np.abs(dbm))]:+5.2f} dB max-dev | {tgt_s}")
print()
print("=" * 72)
print("BAXANDALL (IC5_C) — corner behaviour")
print("=" * 72)
for name, ab, at in [("BASS full boost", 0.0, 0.5), ("BASS full cut", 1.0, 0.5),
                     ("TREBLE full boost", 0.5, 0.0), ("TREBLE full cut", 0.5, 1.0),
                     ("both flat", 0.5, 0.5)]:
    g = 20 * np.log10(np.abs(baxandall_tf(f, ab, at)))
    print(f"{name:>18}: 40Hz {g[np.argmin(np.abs(f-40))]:+6.2f} dB | 100Hz {g[np.argmin(np.abs(f-100))]:+6.2f} | 1kHz {g[np.argmin(np.abs(f-1000))]:+6.2f} | 5kHz {g[np.argmin(np.abs(f-5000))]:+6.2f} | 10kHz {g[np.argmin(np.abs(f-10000))]:+6.2f}")
    # flip sign check: which end is boost
print()
print("=" * 72)
print("IC2_B bridged-T (unloaded approx)")
print("=" * 72)
g = 20 * np.log10(np.abs(bridged_t_tf(f)))
i = np.argmin(g)
print(f"notch: {f[i]:.0f} Hz, depth {g[i]:+.1f} dB; 100Hz {g[np.argmin(np.abs(f-100))]:+.2f} dB; 10kHz {g[np.argmin(np.abs(f-10000))]:+.2f} dB")
print()
print("=" * 72)
print("MASTER [ENG] + GRUNT corner notes")
print("=" * 72)
C36 = 2.2e-6; Rm = 100e3
print(f"MASTER: C36(2u2) into 100k pot->VD: HPF corner = {1/(2*np.pi*C36*Rm):.2f} Hz (inaudible; divider is flat). Unity at full CW; attenuation-only.")
R16, R18 = 6.8e3, 330e3
for A0 in [1e9, 30, 20, 10]:
    zin = R18 / (1 + A0)
    for cname, C in [("4n7", 4.7e-9), ("4n7||47n", 51.7e-9), ("4n7||220n", 224.7e-9)]:
        fc = 1 / (2 * np.pi * C * (R16 + zin))
        print(f"GRUNT {cname:>9} | 4049 open-loop gain {A0 if A0<1e8 else 'ideal':>5}: HPF corner {fc:7.1f} Hz")
    print()
