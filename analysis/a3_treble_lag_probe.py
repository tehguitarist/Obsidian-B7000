#!/usr/bin/env python3.11
"""Phase-9 SESSION 53 — is the model's OD path contributing NON-MINIMUM-PHASE LAG it shouldn't?

THE QUESTION THIS ASKS, AND WHY IT IS NEW.
Session 52 proved that A3's measured target needs ~38 deg MORE LEAD than the minimum-phase
realisation of its own magnitude, and concluded that no causal linear element can supply it. That
proof is about what can be ADDED: minimum phase is the maximum-lead realisation of a given
magnitude, and any other causal realisation is min-phase x all-pass, where the all-pass only adds
LAG. Correct — and it tested exactly one direction.

It never asked the mirror question: **is the MODEL's own OD path already contributing all-pass LAG
that the real pedal does not have?** Removing existing lag is indistinguishable from adding lead,
and it is not bound by the Bode argument at all, because it does not add an element — it corrects
one. A cascade of minimum-phase stages can only be min-phase, so this is only possible where the
model contains a genuine TWO-PATH network whose paths can cancel: a cancellation zero can sit in
the RIGHT half plane, and an RHP zero is precisely an all-pass lag factor.

The OD path has exactly one such network before the clipper: the treble ladder (C5/C9/C6 with
shunts R12/R14) summing against the resistive top rail R7->R8 at node M. It is also the network
that produces GAP #2's ~320 Hz cancellation notch, is the largest pre-clipper roll-off across A3's
span (-7.33 dB, 127->400 Hz), and is `static constexpr` — unreachable from every A3 tool and never
once swept (session 50 next-step (a)).

WHY THIS IS EXACT AND NOT SUBJECT TO SESSION 32's TRAP.
Session 32's Bode/Hilbert phase reconstruction was decided by the UNMEASURED tails of a band-limited
magnitude (36-91 deg of artefact at 20-40 Hz). Here there is no reconstruction and no tail: the
network is small enough to solve SYMBOLICALLY, so we have the exact rational function H(s), its
exact zeros, and therefore its exact min-phase / all-pass factorisation

    H(s) = H_minphase(s) . A(s),     A(s) = product over RHP zeros z of (s - z)/(s + conj(z))

with |A(jw)| = 1 identically (asserted numerically as a self-check). `-arg A(j.2.pi.f)` IS the lag
the model's own non-minimum-phase content contributes, computed with zero free assumptions.

VERDICT TO READ: if that excess lag is roughly FLAT and near +38 deg across 40 Hz - 1.6 kHz, then
A3's "impossible" phase requirement is not impossible at all — it is the model carrying an all-pass
factor the pedal does not, and the fix is a ladder rebalance, pre-clipper, exactly where session
53's drive-independence audit says the carrier is free to live.

Run:  /opt/homebrew/bin/python3.11 -u analysis/a3_treble_lag_probe.py
"""
import contextlib
import io
import itertools
import math
import os
import sys

import numpy as np
import sympy as sp

sys.path.insert(0, "analysis")
# eq_reference runs a large diagnostic report at MODULE level (no __main__ guard), which would
# otherwise bury this tool's own output. Swallow it on import only.
with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ

# Shipped values. R7/R8/R11/R12/R13/R14 and C5/C9/C6 are TrebleAttack.h's static constexpr;
# C7 and RdampC5 are the two that FitParams can already reach (680p fitted vs 100n schematic,
# and the session-19 ladder damping).
SHIPPED = dict(R7=200e3, R8=470e3, R11=470e3, R12=6.8e3, R13=1e6, R14=22e3,
               C5=22e-9, C9=22e-9, C6=22e-9, C7=680e-12, RdampC5=30e3)

# A3's fit band (session 52 item 1).
F_LO, F_HI = 40.0, 1613.0
BANDS = np.array([40, 50, 64, 80, 101, 127, 160, 202, 254, 320, 403, 508, 640, 806, 1016, 1281, 1613],
                 dtype=float)

TARGET_LEAD_DEG = 38.0   # session 52's near-constant excess lead over 40 Hz - 1.6 kHz


def H_symbolic(p):
    """Exact H(s) = V(Q)/V(G) for the treble network, ATTACK = flat, ideal source at G.

    Node graph (circuit.md "Treble network + ATTACK", verified 2026-07-19; same as
    eq_reference.treble_attack_tf's docstring):
        G --R7--> M --R8--> P
        G --C5(+RdampC5)--> L1 --C9--> L2 --C6--> M
        L1 --R12--> GND ;  L2 --R14--> GND
        P --R11--> GND ;  P --C7--> Q ;  Q --R13--> GND
    ATTACK flat = C8's pole open, so C8 is absent.
    """
    s = sp.symbols("s")
    M, P, L1, L2, Q = sp.symbols("M P L1 L2 Q")
    G = sp.Integer(1)

    def gR(r):
        return sp.Rational(1) / sp.nsimplify(r, rational=True)

    yC5 = s * sp.nsimplify(p["C5"], rational=True)
    if p["RdampC5"] > 0.0:                      # lossy C5: series Rd + C5 as one admittance
        yC5 = yC5 / (1 + yC5 * sp.nsimplify(p["RdampC5"], rational=True))
    yC9 = s * sp.nsimplify(p["C9"], rational=True)
    yC6 = s * sp.nsimplify(p["C6"], rational=True)
    yC7 = s * sp.nsimplify(p["C7"], rational=True)

    eqs = [
        sp.Eq((M - G) * gR(p["R7"]) + (M - P) * gR(p["R8"]) + (M - L2) * yC6, 0),
        sp.Eq((P - M) * gR(p["R8"]) + P * gR(p["R11"]) + (P - Q) * yC7, 0),
        sp.Eq((L1 - G) * yC5 + (L1 - L2) * yC9 + L1 * gR(p["R12"]), 0),
        sp.Eq((L2 - L1) * yC9 + (L2 - M) * yC6 + L2 * gR(p["R14"]), 0),
        sp.Eq((Q - P) * yC7 + Q * gR(p["R13"]), 0),
    ]
    sol = sp.solve(eqs, [M, P, L1, L2, Q], dict=True)[0]
    return s, sp.cancel(sp.together(sol[Q]))


def poly_roots(s, H):
    """(zeros, poles, gain) of the exact rational function."""
    num, den = sp.fraction(sp.cancel(H))
    nz = [complex(c) for c in sp.Poly(sp.expand(num), s).all_coeffs()]
    np_ = [complex(c) for c in sp.Poly(sp.expand(den), s).all_coeffs()]
    return np.roots(nz), np.roots(np_), nz[0] / np_[0]


def allpass_lag_deg(zeros, f):
    """-arg A(j2pi f) in degrees, A = product (s - z)/(s + conj(z)) over RHP zeros. Also |A|."""
    jw = 2j * np.pi * np.asarray(f, dtype=float)
    rhp = [z for z in zeros if z.real > 1e-9]
    A = np.ones_like(jw, dtype=complex)
    for z in rhp:
        A *= (jw - z) / (jw + np.conj(z))
    return -np.degrees(np.angle(A)), np.abs(A), rhp


def check_against_oracle(p):
    """The symbolic H must reproduce eq_reference.treble_attack_tf (Zs=None) exactly."""
    s, H = H_symbolic(p)
    f = np.array([40.0, 101.0, 320.0, 1016.0, 5000.0])
    Hf = np.array([complex(H.subs(s, complex(2j * np.pi * x))) for x in f], dtype=complex)
    ref = EQ.treble_attack_tf(f, "flat", Zs=None, **{k: v for k, v in p.items()})
    dmag = 20 * np.log10(np.abs(Hf) / np.abs(ref))
    dph = np.degrees(np.angle(Hf / ref))
    print("  f(Hz)      dMag(dB)   dPhase(deg)")
    for i, x in enumerate(f):
        print(f"  {x:8.0f}   {dmag[i]:9.6f}   {dph[i]:10.6f}")
    ok = np.max(np.abs(dmag)) < 1e-6 and np.max(np.abs(dph)) < 1e-4
    print("  => symbolic H %s the oracle\n" % ("MATCHES" if ok else "DISAGREES WITH"))
    return ok


def inband_mask():
    return (BANDS >= F_LO) & (BANDS <= F_HI)


def main():
    print("=== 1. SELF-CHECK: symbolic H(s) vs eq_reference.treble_attack_tf ===\n")
    if not check_against_oracle(SHIPPED):
        sys.exit("self-check FAILED — the node equations do not reproduce the oracle; fix before reading anything below")

    print("=== 2. EXACT POLE/ZERO MAP OF THE SHIPPED TREBLE NETWORK (ATTACK flat) ===\n")
    s, H = H_symbolic(SHIPPED)
    zeros, poles, k = poly_roots(s, H)
    print("  zeros (rad/s, and Hz where real):")
    for z in sorted(zeros, key=lambda z: abs(z)):
        tag = "  <-- RIGHT HALF PLANE" if z.real > 1e-9 else ""
        print(f"    {z.real:+14.4f} {z.imag:+14.4f}j   |z|/2pi = {abs(z)/(2*np.pi):10.2f} Hz{tag}")
    print("  poles (rad/s):")
    for pl in sorted(poles, key=lambda z: abs(z)):
        print(f"    {pl.real:+14.4f} {pl.imag:+14.4f}j   |p|/2pi = {abs(pl)/(2*np.pi):10.2f} Hz")

    lag, mag, rhp = allpass_lag_deg(zeros, BANDS)
    print(f"\n  RHP zero count: {len(rhp)}")
    print(f"  |A(jw)| deviation from 1 (must be ~0): {np.max(np.abs(mag - 1.0)):.2e}")

    if not rhp:
        print("\n  The SHIPPED network is MINIMUM PHASE — no all-pass lag at this setting.")
        print("  But one setting is not the question: CAN this topology be non-minimum-phase at")
        print("  all? A two-path cancellation is where RHP zeros come from, and the shipped state")
        print("  has trebleLadderDampR = 30k, which session 46 showed DESTROYS the notch. If some")
        print("  plausible ladder puts zeros in the RHP, the PEDAL could sit there while the model")
        print("  does not — so the refutation is only general if no setting does.\n")
        print("=== 3. CAN THE LADDER BE NON-MINIMUM-PHASE AT ANY PLAUSIBLE SETTING? ===\n")
        # Sweep the ladder's own degrees of freedom over a wide, physically plausible range:
        # the three series caps, the two shunt resistors, the two top-rail resistors, and the
        # session-19 damping R (whose schematic value is 0 -- the deep-notch end).
        grid = {
            "RdampC5": [0.0, 1e3, 10e3, 30e3, 100e3],
            "C5": [4.7e-9, 22e-9, 100e-9],
            "C9": [4.7e-9, 22e-9, 100e-9],
            "C6": [4.7e-9, 22e-9, 100e-9],
            "R12": [1.5e3, 6.8e3, 33e3],
            "R14": [4.7e3, 22e3, 100e3],
        }
        keys = list(grid)
        combos = list(itertools.product(*(grid[k] for k in keys)))
        print(f"  sweeping {len(combos)} ladder settings ({' x '.join(f'{k}:{len(grid[k])}' for k in keys)})")
        worst = []
        n_rhp = 0
        for combo in combos:
            p = dict(SHIPPED, **dict(zip(keys, combo)))
            try:
                s2, H2 = H_symbolic(p)
                z2, _, _ = poly_roots(s2, H2)
            except Exception:
                continue
            r2 = [z for z in z2 if z.real > 1e-9]
            if r2:
                n_rhp += 1
                lag2, _, _ = allpass_lag_deg(z2, BANDS)
                worst.append((lag2[inband_mask()].mean(), p, lag2))
        print(f"  settings with ANY right-half-plane zero: {n_rhp} of {len(combos)}")
        if n_rhp == 0:
            print("\n=== 4. VERDICT ===")
            print("  => The treble network is MINIMUM PHASE across its ENTIRE plausible parameter")
            print("     space, not merely at the shipped values. Its zeros are structurally")
            print("     confined to the left half plane, so NO ladder rebalance can supply excess")
            print("     lead, and the 'model is carrying all-pass lag' hypothesis is REFUTED for")
            print("     this network — generally, not just at one point.")
            print("     ⚠ Scope: this covers the treble network in isolation, ATTACK flat, ideal")
            print("     source. It does NOT clear the OTHER two-path candidate in the OD path (the")
            print("     IC2_B bridged-T, post-clipper) nor the clipper's own feedback loop, where a")
            print("     memoryless nonlinearity inside reactive feedback is not an LTI transfer at")
            print("     all and no pole/zero argument applies.")
            print("     ▶ Task #2 should NOT proceed on the phase argument. The ladder may still")
            print("       matter for A3's MAGNITUDE (C1/C2), which is a separate, live question.")
        else:
            best = max(worst, key=lambda t: t[0])
            print(f"  best mean available lead over {F_LO:.0f}-{F_HI:.0f} Hz: {best[0]:.1f} deg")
            print(f"  at {best[1]}")
            print("\n=== 4. VERDICT ===")
            print("  => The topology CAN be non-minimum-phase. Report the settings and proceed to")
            print("     plumb the ladder; the pedal may sit in the RHP regime while the model does not.")
        return

    print("\n=== 3. THE ALL-PASS LAG THE MODEL IS CARRYING ===\n")
    print("  -arg A(f) = lag contributed by the RHP zero(s) = the lead that would be recovered")
    print(f"  if this network were minimum phase. Session 52's requirement is ~{TARGET_LEAD_DEG:.0f} deg, roughly flat.\n")
    print(f"  {'f(Hz)':>8} {'excess_lag(deg)':>17}")
    for b, L in zip(BANDS, lag):
        print(f"  {b:8.0f} {L:17.1f}")
    inband = inband_mask()
    print(f"\n  over {F_LO:.0f}-{F_HI:.0f} Hz:  mean {lag[inband].mean():.1f} deg, "
          f"min {lag[inband].min():.1f}, max {lag[inband].max():.1f}, "
          f"spread {lag[inband].max()-lag[inband].min():.1f}")

    print("\n=== 4. VERDICT ===")
    mean_lag = lag[inband].mean()
    spread = lag[inband].max() - lag[inband].min()
    print(f"  mean available lead  = {mean_lag:.1f} deg   (need ~{TARGET_LEAD_DEG:.0f})")
    print(f"  flatness (spread)    = {spread:.1f} deg")
    if mean_lag >= 0.5 * TARGET_LEAD_DEG and spread <= 1.5 * TARGET_LEAD_DEG:
        print("\n  => REACHABLE IN PRINCIPLE. The model's treble network carries non-minimum-phase")
        print("     lag of the right order across A3's whole span. Session 52's impossibility is")
        print("     an impossibility for ADDED post-clipper elements only; correcting the lag the")
        print("     model already has is a different operation and is not Bode-bound.")
        print("     ▶ PROCEED to task #2: plumb the ladder into FitParams and fit it, gating on")
        print("       the null (a3_lead_fit), the SIDE monitors, and the 63-capture matrix.")
    else:
        print("\n  => NOT of the right size/shape. The network is non-minimum-phase, but its")
        print("     all-pass lag does not match session 52's requirement, so a ladder rebalance")
        print("     is not on its own the answer. Record as measured and do not plumb on this basis.")


if __name__ == "__main__":
    main()
