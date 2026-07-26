#!/usr/bin/env python3.11
"""clipper_rail_selfconsistent — what supply does IC3 (CD4049UBE) ACTUALLY sit at?

WHY (session 42, Phase 9 / A5)
------------------------------
A5 exposed a genuine contradiction between two physical arguments about `kInputRef`:

  • THE CLEAN PATH (session 41, clean_headroom_bound.py) says K <= ~1.5 V/FS. IC5_B's fixed
    -2.2x gain is upstream of every EQ band, and at K = 3.377 the -3 dBFS rung needs 5.260 V
    of swing where the 9 V supply allows +/-4.325 V. The pedal measures 0.0000 % THD there.
    That is an IMPOSSIBILITY, not a preference.

  • THE CLIPPER (session 17, GainStaging.h) says K ~ 3.4. Matching the captured harmonic ramp
    at a lower K forces the clipper's ceilings down; at K = 0.87 the fit wanted ~1.3 V/side,
    which session 17 rejected as far below "the ~7 V R19-dropped rail".

Both are output-swing-vs-supply arguments, so they are the same KIND of claim -- which is why
they cannot simply be traded off against each other. But the second one leans on a number that
has never been computed: **what IS the R19-dropped rail?** circuit.md carries a PRIOR ("the
class-A linear-region current, mA-scale, drops ~0.5-3 V"), not a derivation, and session 17
compared its fitted 4.94 V sum against a round "~7 V" that appears in no calculation.

This script derives it, and it needs no capture and no fit -- only the DAFx-2020 fitted device
model plus one resistor:

  R19 = 1 k in series from the +9 V rail (post-D3, 8.65 V) to IC3's VDD pin. IC3 is the ONLY
  IC on the board with a supply dropper (circuit.md, R1-R54 reconciled). So

      VDD = V_RAIL - I_DD(VDD) * R19

  is an implicit equation, because the crowbar current ITSELF depends on VDD. That feedback is
  the whole point and it is what a fixed "0.5-3 V drop" prior misses: as VDD falls, both
  transistors' overdrive falls, the through-current collapses roughly quadratically, and the
  drop shrinks -- so the operating point is self-limiting and cannot run away to a low rail.

DEVICE MODEL (docs/nonlinear-component-modeling.md §1, from DAFx-2020 "Taming the Red Llama",
Köper & Holters -- a fit to the REAL device, docs/refs/):
    n-ch: alpha = 5.1021e-3 A/V^2, vT = +1.5702 V
    p-ch: alpha = 8.2246e-4 A/V^2, vT = -0.48476 V, lambda = 0.06 /V

At the self-bias point the inverter's input and output both sit at the trip voltage Vm (that is
what the R18 shunt feedback enforces), and BOTH transistors are saturated and carry the same
current. Solving Id_n(Vm) = Id_p(Vm) gives Vm, and that common current IS the crowbar current.

⚠ WHAT THIS DOES AND DOES NOT SETTLE. It bounds the CD4049's available output swing, i.e. the
physical ceiling on `clipSatLo + clipSatHi`. It does NOT measure kInputRef. Read it as: "a
clipSat sum above this is impossible, and a sum far below it wants an explanation" -- the same
shape of statement the clean path makes about IC5_B, so the two are finally comparable.

Run: /opt/homebrew/bin/python3.11 analysis/clipper_rail_selfconsistent.py
"""
import numpy as np

# ---- Supply / board facts (circuit.md; NOT fitted) -------------------------------------
V_SUPPLY = 9.0
V_D3 = 0.35            # D3 1N5817 Schottky forward drop
V_RAIL = V_SUPPLY - V_D3   # 8.65 V — the op-amp rail
R19 = 1.0e3            # the CD4049's supply dropper — the only one on the board

# ---- DAFx-2020 fitted CD4049UB section (docs/nonlinear-component-modeling.md §1) --------
AN, VTN = 5.1021e-3, 1.5702      # n-channel
AP, VTP = 8.2246e-4, 0.48476     # p-channel (|vT|)
LAMBDA_P = 0.06                  # p-ch channel-length modulation

# The hex inverter has 6 sections. Only ONE carries signal (IC3 pin 3 -> pin 2). The other five
# draw crowbar current ONLY if their inputs sit near mid-rail; an input tied to a rail draws the
# datasheet's quiescent 0.02 uA (i.e. nothing). Neither schematic records what happens to the
# unused inputs, so BOTH cases are reported rather than one being assumed.
N_SECTIONS = (1, 6)


def crowbar_current(vdd):
    """Through-current (A) of one self-biased inverter section at supply `vdd`.

    At the shunt-feedback self-bias point Vin = Vout = Vm, both devices are in saturation and
    carry equal current. Solve Id_n(Vm) == Id_p(Vm) for Vm by bisection on the (monotone)
    difference, then return that common current.
    """
    def id_n(vm):
        vov = vm - VTN
        return 0.5 * AN * vov * vov if vov > 0.0 else 0.0

    def id_p(vm):
        vov = (vdd - vm) - VTP
        if vov <= 0.0:
            return 0.0
        # Vsd = vdd - vm at the trip point
        return 0.5 * AP * vov * vov * (1.0 + LAMBDA_P * (vdd - vm))

    # If the supply cannot turn both devices on at once there is no crowbar path at all.
    if vdd <= VTN + VTP:
        return 0.0, float("nan")
    lo, hi = VTN, vdd - VTP          # region where both are on
    if lo >= hi:
        return 0.0, float("nan")
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if id_n(mid) - id_p(mid) > 0.0:
            hi = mid                  # too much n-current -> lower Vm
        else:
            lo = mid
    vm = 0.5 * (lo + hi)
    return id_n(vm), vm


def solve_vdd(n_sections):
    """Self-consistent VDD: VDD = V_RAIL - n * I(VDD) * R19, by damped fixed-point iteration."""
    vdd = V_RAIL
    for _ in range(500):
        i, _vm = crowbar_current(vdd)
        new = V_RAIL - n_sections * i * R19
        new = max(new, 0.0)
        if abs(new - vdd) < 1e-12:
            vdd = new
            break
        vdd += 0.5 * (new - vdd)      # damping: the loop gain is steep near the rail
    i, vm = crowbar_current(vdd)
    return vdd, i, vm


def main():
    print("=" * 96)
    print("A5 — the CD4049's SELF-CONSISTENT supply rail, and what it allows clipSat to be")
    print("=" * 96)
    print(f"  +9 V - D3 ({V_D3:.2f} V) = {V_RAIL:.2f} V feeding R19 = {R19/1e3:.0f} k -> IC3 VDD")
    print(f"  device: DAFx-2020 fit — n-ch a={AN:.4e} vT={VTN:+.4f} | "
          f"p-ch a={AP:.4e} vT={-VTP:+.4f} lambda={LAMBDA_P}")
    print()

    # ---- (1) the open-loop picture: current vs an IMPOSED supply -----------------------
    print("-" * 96)
    print("(1) CROWBAR CURRENT vs SUPPLY (one section, self-biased) — note how fast it collapses")
    print("-" * 96)
    print(f"  {'VDD (V)':>8} | {'Vm (V)':>7} | {'I (mA)':>8} | {'drop I*R19 (V)':>14}")
    for vdd in (8.65, 8.0, 7.0, 6.0, 5.0, 4.0, 3.0, 2.5, 2.0):
        i, vm = crowbar_current(vdd)
        print(f"  {vdd:>8.2f} | {vm:>7.3f} | {i*1e3:>8.3f} | {i*R19:>14.3f}")
    print("  ⇒ the current is a strong (super-quadratic) function of VDD, so the drop is")
    print("    SELF-LIMITING: a low rail cannot sustain the current that would be needed to")
    print("    produce it. This is what a fixed '0.5-3 V drop' prior cannot express.")
    print()

    # ---- (2) the self-consistent operating point ---------------------------------------
    print("-" * 96)
    print("(2) SELF-CONSISTENT OPERATING POINT   VDD = V_RAIL - n*I(VDD)*R19")
    print("-" * 96)
    print(f"  {'sections':>8} | {'VDD (V)':>8} | {'I_tot (mA)':>10} | {'drop (V)':>9} | {'Vm (V)':>7}")
    results = {}
    for n in N_SECTIONS:
        vdd, i, vm = solve_vdd(n)
        results[n] = vdd
        print(f"  {n:>8d} | {vdd:>8.3f} | {n*i*1e3:>10.3f} | {V_RAIL-vdd:>9.3f} | {vm:>7.3f}")
    print("  (1 section = unused inputs tied to a rail, the correct CMOS practice;")
    print("   6 sections = the pessimistic case where every unused input floats at mid-rail)")
    print()

    # ---- (3) what that allows clipSat to be --------------------------------------------
    print("-" * 96)
    print("(3) THE CONSEQUENCE FOR clipSat  (Clipper.h: satLo/satHi are OUTPUT SWING toward the")
    print("    GND and +VDD rails respectively, so their SUM is the total available swing)")
    print("-" * 96)
    print(f"  datasheet output levels: VOL ~ 0.05 V, VOH ~ VDD - 0.05  =>  swing ~ VDD")
    print(f"  datasheet RECOMMENDED VCC range: 3 - 18 V (a rail under 3 V is out of spec)")
    print()
    shipped = 2.0067 + 2.9321
    for n, vdd in results.items():
        print(f"  n={n}: available swing ~ {vdd:.2f} V   "
              f"=> shipped clipSat sum {shipped:.3f} V is {shipped/vdd*100:.0f} % of it")
    print()
    print("  Session-17's comparison was against a round '~7 V rail' that no calculation produced.")
    print("  Read the numbers above against BOTH candidate values of kInputRef:")
    k_ship, k_clean = 3.377, 1.509
    print(f"    K = {k_ship:.3f} (shipped)      -> clipSat sum {shipped:.3f} V")
    print(f"    K = {k_clean:.3f} (clean bound) -> clipSat sum ~{shipped*k_clean/k_ship:.3f} V "
          f"(if the operating point just scales)")
    for n, vdd in results.items():
        lo = shipped * k_clean / k_ship
        print(f"      vs n={n} self-consistent rail {vdd:.2f} V: "
              f"shipped = {shipped/vdd*100:.0f} %, clean-bound = {lo/vdd*100:.0f} %")
    print()
    print("  ⚠ 'clipSat sum scales with K' is an APPROXIMATION — the degeneracy is exact for the")
    print("    clipper ALONE, and is broken by the JFET's fixed thresholds and the fixed-volt")
    print("    RailClamps upstream. The fitted number is what fit_nonlinear.py actually returns;")
    print("    the scaled figure above is only for orientation.")


if __name__ == "__main__":
    main()
