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

f = np.logspace(np.log10(10), np.log10(20000), 1200)

print("=" * 72)
print("MID STAGES — peak centre & gain vs C33/C35 (pot full boost a=0 -> check!)")
print("=" * 72)
# which pot extreme is boost? try both ends; magnitude peak
for band, caps, targets in [
    ("LO-MID (C33)", [("47n", 47e-9, 250), ("22n STOCK-board", 22e-9, None), ("10n", 10e-9, 500), ("2n2", 2.2e-9, 1000)], None),
    ("HI-MID (C35)", [("15n", 15e-9, 750), ("3n3", 3.3e-9, 1500), ("820p", 820e-12, 3000), ("680p STOCK-board", 680e-12, None)], None),
]:
    for name, C, tgt in caps:
        g_end0 = mid_stage_tf(f, 0.0, C)
        g_end1 = mid_stage_tf(f, 1.0, C)
        g_mid = mid_stage_tf(f, 0.5, C)
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
