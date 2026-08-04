#!/usr/bin/env python3.11
"""A5 step 2 — what does the PEDAL's own clean capture allow `kInputRef` to be?

`clean_rail_probe.cpp` localises the model's clean-path defect (IC5_B, the fixed −2.2 EqPreGain
stage, is the first node to rail). This script asks the complementary question, and it needs no
model at all beyond two schematic-verified facts:

  • IC5_B's gain is −R29/R28 = −22k/10k = −2.2, fixed, always in circuit (circuit.md, BOM-reconciled).
  • The pedal runs off ONE 9 V supply: 9 V → D3 (1N5817, ~0.35 V) → +8.65 V rail, VD = 4.32 V
    (circuit.md "Supply"). So NO node inside this pedal can swing more than ±4.32 V about VD —
    not with a better op-amp, not with a different rail estimate. That is a supply ceiling, not a
    TL07x parameter.

`kInputRef` converts capture dBFS to volts at the jack, and the reamp rig is unity round-trip
(bypass.wav, −0.012 dB — GainStaging.h), so:

    V(IC5_B) at rung R  =  kInputRef · 10^(R/20) · 2.2

The pedal is at its measurement floor (0.0000% THD) at EVERY rung of the 1 kHz `lvl_` ladder,
including the hottest, −3 dBFS (session 39). Requiring that swing to be POSSIBLE gives a hard
upper bound on kInputRef — one the clipper has no part in, which matters because kInputRef and
the clipper ceilings are degenerate under audio-only captures and session 17 could only pin
kInputRef by fitting the pair jointly (GainStaging.h).

A second, even more model-free bound comes from the OUTPUT: whatever the pedal's clean gain
actually is, its own output node cannot exceed the same ±4.32 V either, and the recorded output
level is a direct measurement.

Run: /opt/homebrew/bin/python3.11 analysis/clean_headroom_bound.py
"""
import sys, os

sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import captures as C

CAP_DIR = "analysis/captures"

# ---- Supply / stage facts (circuit.md; NOT fitted) --------------------------------------
V_RAIL = 9.0 - 0.35        # D3 1N5817 forward drop
VD = V_RAIL / 2.0          # R30/R31 10k/10k divider
V_SUPPLY_SWING = VD        # absolute max excursion about VD, any node, any op-amp
RAIL_POS = 2.7             # TL07x output limit, session 21 (DERIVED from the above, not fitted)
RAIL_KNEE = 0.35           # RailClamp.h: soft compression starts RAIL_KNEE below the hard limit
EQPREGAIN = 22.0e3 / 10.0e3  # |−R29/R28|

K_SHIPPED = 3.377          # session-17 kInputRef — the number A5 put UNDER TEST. Kept as a
                           # labelled historical control so session 44's quote stays reproducible.
K_SHIPPED_NOW = 0.90       # GainStaging.h, session-109 (the value the plugin actually ships)

# ⭐⭐ SESSION 142 — WHICH OF THIS TOOL'S BOUNDS ACTUALLY BINDS, AND WHY IT MATTERS FOR ITEM 4.
# The fence every clipper fit since session 44 has been run against is `kInputRef <= 1.509`, and
# that is `k_clean` from SECTION (1): (RAIL_POS - RAIL_KNEE) / (EQPREGAIN * 10^(-3/20)) = 2.35 /
# (2.2 * 0.70795). Every term is schematic-derived — the 8.65 V rail, VD, IC5_B's fixed -2.2, the
# session-21 TL07x rails, and the hottest ladder rung. ** NO CAPTURE ENTERS IT. **
# Section (2)'s capture-derived bounds come out at 4.375-5.493, i.e. 2.9-3.6x LOOSER, so they do
# not bind and never have.
# ⇒ CONSEQUENCE FOR OPEN-WORK ITEM 4: this tool is on item 4's list of consumers of the corrupted
#   `master-1700_gain-n12_base-clean.wav` (GATE T: 4.447 dB low), and that is correct — but the
#   corruption reaches ONLY a non-binding column of section (2). Re-pointing it CANNOT move the
#   1.509 fence, so it cannot unlock the physical-clipSat re-fit that open-work item 5 proposed.
#   Measured, not argued. (Item 5 is separately refuted outright — FitParams.h's clipSat block.)
# ⚠ AND THAT ROW IS DOUBLY UNUSABLE AS A BOUND, for a reason worth stating so nobody quotes it:
#   section (2) reads the -3 dBFS rung, which is exactly the ONE segment session 115 measured as
#   PINNED in that file (peak 0.98850, -0.10 dBFS). So its `out@-3 dBFS` is a ceiling, not a level,
#   on top of the mis-dialled knob. It is printed, and it must not be quoted.

HOTTEST_RUNG_DB = -3.0     # gen_test_signal.py::LEVEL_STEPS_DB tops out here
RUNGS = list(range(-36, -2, 3))


def seg_peak_dbfs(x, name):
    s = A.seg_of(x, name)
    return 20 * np.log10(np.max(np.abs(s)) + 1e-20)


def main():
    orig = A.load(A.ORIG)

    print("=" * 100)
    print("A5 — how hot can kInputRef be, given the pedal's own supply and its clean captures?")
    print("=" * 100)
    print(f"  +9 V − D3 ({0.35:.2f} V) = {V_RAIL:.2f} V rail;  VD = {VD:.3f} V")
    print(f"  => ABSOLUTE swing ceiling at any node: ±{V_SUPPLY_SWING:.3f} V (supply, not op-amp)")
    print(f"  => TL07x derived output limit (session 21): +{RAIL_POS:.2f} V, soft from "
          f"+{RAIL_POS - RAIL_KNEE:.2f} V")
    print(f"  IC5_B (EqPreGain) gain = {EQPREGAIN:.2f}×, fixed and always in circuit")
    print()

    # ---------------------------------------------------------------- (1) the IC5_B bound
    print("-" * 100)
    print("(1) BOUND FROM IC5_B's REQUIRED SWING — the pedal is clean at every rung, so the swing")
    print("    kInputRef implies at the hottest rung must at least be POSSIBLE")
    print("-" * 100)
    v_in_pk = K_SHIPPED * 10 ** (HOTTEST_RUNG_DB / 20.0)
    v_ic5b = v_in_pk * EQPREGAIN
    print(f"  at {HOTTEST_RUNG_DB:+.0f} dBFS with kInputRef = {K_SHIPPED}:")
    print(f"    jack   {v_in_pk:6.3f} V pk")
    print(f"    IC5_B  {v_ic5b:6.3f} V pk   vs supply ceiling {V_SUPPLY_SWING:.3f} V"
          f"   vs TL07x soft onset {RAIL_POS - RAIL_KNEE:.2f} V")
    over_supply = v_ic5b > V_SUPPLY_SWING
    print(f"    => {'IMPOSSIBLE on this supply' if over_supply else 'possible'}"
          f" ({20 * np.log10(v_ic5b / V_SUPPLY_SWING):+.2f} dB vs the supply ceiling)")
    k_supply = V_SUPPLY_SWING / (EQPREGAIN * 10 ** (HOTTEST_RUNG_DB / 20.0))
    k_rail = RAIL_POS / (EQPREGAIN * 10 ** (HOTTEST_RUNG_DB / 20.0))
    k_clean = (RAIL_POS - RAIL_KNEE) / (EQPREGAIN * 10 ** (HOTTEST_RUNG_DB / 20.0))
    print()
    print(f"  kInputRef ceilings implied (V/FS)   [session-17 value under test = {K_SHIPPED}; "
          f"SHIPPED now = {K_SHIPPED_NOW}]:")
    print(f"    ≤ {k_supply:.3f}   supply ceiling — no op-amp on this rail can beat it")
    print(f"    ≤ {k_rail:.3f}   TL07x hard limit (session-21 derived rails)")
    print(f"    ≤ {k_clean:.3f}   TL07x knee — the level at which distortion actually STARTS,")
    print(f"              i.e. what 'the pedal reads 0.0000% THD at −3 dBFS' actually requires")
    print(f"    ** THIS IS THE BINDING FENCE, AND IT IS CAPTURE-FREE (s142) ** — every term is "
          f"schematic-derived,\n       so no capture correction anywhere can relax it.  Shipped K "
          f"({K_SHIPPED_NOW}) has {20 * np.log10(k_clean / K_SHIPPED_NOW):.2f} dB of headroom "
          f"left to it (x{k_clean / K_SHIPPED_NOW:.3f}).")

    # ---- s142: the closed-form question open-work item 5 actually turned on --------------
    SATSUM, VDD_CLIP = 0.4377 + 0.59791, 5.636     # FitParams.h (s44 A5) / circuit.md (s42 solve)
    L = VDD_CLIP / SATSUM
    k_req = K_SHIPPED_NOW * L
    print()
    print(f"  ITEM 5 (s142) — could a PHYSICAL clipper ceiling ever be driven on this supply?")
    print(f"    shipped clipSat sum {SATSUM:.4f} V is {100 * SATSUM / VDD_CLIP:.1f} % of the "
          f"{VDD_CLIP} V rail  =>  needs x{L:.3f} ({20 * np.log10(L):+.2f} dB)")
    print(f"    the VTC is homogeneous and every stage jack->node W is schematic-fixed, so the only")
    print(f"    free scalar is kInputRef:  {K_SHIPPED_NOW} x {L:.3f} = {k_req:.3f} V/FS required")
    print(f"    vs the ABSOLUTE supply ceiling {k_supply:.3f}  =>  over by x{k_req / k_supply:.2f} "
          f"({20 * np.log10(k_req / k_supply):+.2f} dB)  ** INFEASIBLE **")
    print(f"    K at that absolute ceiling supplies only {100 * (k_supply / K_SHIPPED_NOW) / L:.1f} "
          f"% of the needed scale "
          f"({100 * (k_clean / K_SHIPPED_NOW) / L:.1f} % to the binding fence).")

    # ------------------------------------------------ (2) the model-free output-node bound
    print()
    print("-" * 100)
    print("(2) BOUND FROM THE PEDAL'S OWN OUTPUT LEVEL — model-free: whatever its clean gain is,")
    print("    the recorded output cannot have exceeded the same ±%.2f V" % V_SUPPLY_SWING)
    print("-" * 100)
    print(f"{'capture':<42}{'master':>8}{'out@-3 dBFS':>13}{'clean gain':>12}{'kInputRef ≤':>13}")
    print("-" * 100)
    cands = [
        "ref-clean.wav",
        "master-1700_gain-n12_base-clean.wav",
        "master-0930_base-clean.wav",
        "bass-0930_base-clean.wav",
    ]
    for name in cands:
        path = os.path.join(CAP_DIR, name)
        if not os.path.exists(path):
            print(f"{name:<42}(missing)")
            continue
        parsed = C.parse_capture(name)
        cap = C.load_capture(path)
        if not A.is_full_length(cap, orig):
            print(f"{name:<42}(short/truncated)")
            continue
        ped, _ = A.align(cap, orig)
        out_db = seg_peak_dbfs(ped, f"lvl_{int(HOTTEST_RUNG_DB)}")
        # The rung's level at the jack: nominal, plus this capture's MEASURED session trim
        # (never the nominal −12 dial — session 21: the measured value is −12.071 dB).
        # gain_correction_db() is the dB to ADD to the capture to restore the reference frame,
        # so the level that actually reached the jack was that much LOWER.
        in_db = HOTTEST_RUNG_DB - C.gain_correction_db(parsed)
        gain_db = out_db - in_db
        k_out = V_SUPPLY_SWING / 10 ** (out_db / 20.0)
        print(f"{name:<42}{parsed.get('master', float('nan')):>8.2f}{out_db:>12.2f} dB"
              f"{gain_db:>+11.2f} dB{k_out:>12.3f}")

    print()
    print("  'clean gain' is the pedal's measured jack-to-jack voltage gain on that rung — compare")
    print("  it against the schematic chain (IC5_B −2.2 × Baxandall ≈ 0.93 × mids ×1 × MASTER divider),")
    print("  which is +6.7 dB at master max BEFORE the divider. A large positive difference is")
    print("  unmodelled gain, and `kOutputMakeup` is currently absorbing it.")
    print("  ⚠ s142: the line above used to name `kOutputMakeup` = 3.684 (+11.33 dB). Session 115")
    print("    shipped 4.3297 (GATE T: the old anchor capture was 4.447 dB low). Do not quote 3.684.")
    print("  ⛔ s142: the `master-1700_gain-n12_base-clean.wav` row is NOT a usable bound — its")
    print("    −3 dBFS rung is the one segment session 115 measured PINNED (peak 0.98850), so its")
    print("    `out@-3 dBFS` is a ceiling rather than a level, on top of the mis-dialled knob. It")
    print("    does not bind (see section 1), so nothing downstream depends on it — but do not quote it.")

    # ------------------------------------------------------- (3) the pedal's ladder, for the record
    print()
    print("-" * 100)
    print("(3) THE PEDAL'S OWN LADDER — output peak per rung on ref-clean (linearity check: the")
    print("    steps must be exactly 3 dB apart if nothing in the pedal is compressing)")
    print("-" * 100)
    path = os.path.join(CAP_DIR, "ref-clean.wav")
    ped, _ = A.align(C.load_capture(path), orig)
    prev = None
    devs = []
    print(f"{'rung':>7}{'out pk dBFS':>14}{'step':>9}")
    for db in RUNGS:
        v = seg_peak_dbfs(ped, f"lvl_{db}")
        step = "" if prev is None else f"{v - prev:+.3f}"
        if prev is not None:
            devs.append(abs((v - prev) - 3.0))
        print(f"{db:>7}{v:>13.3f} {step:>9}")
        prev = v
    print(f"\n  worst deviation from an exact 3.000 dB step: {max(devs):.4f} dB  =>  "
          f"{'PASS — the pedal is linear across the whole ladder' if max(devs) < 0.1 else 'CHECK'}")


if __name__ == "__main__":
    main()
