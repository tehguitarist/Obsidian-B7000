#!/usr/bin/env python3.11
"""W2 (item 13) — does counting the clean path's OWN first-order LF corners predict the ~2.0-2.5x
multiple session 167 measured between the pedal-model phase residual and a single 7.2->12.2 Hz
corner-shift unit?

No captures, no render, no fit -- every number here is a closed-form 1/(2*pi*R*C) read straight
from the shipped source (cited per corner), so this is reproducible from `src/dsp/` alone and
needs no DSP change (W2's own rule).

Background (docs/session-log.md SESSION 167 addendum, item 13): the clean-path phase residual
(pedal minus model, `analysis/null_review_gate.py`'s captures) divided by the phase of ONE
first-order corner moved from 7.2 Hz to 12.2 Hz (exactly session 91's `c21R` re-anchor, 220k ->
130k) is flat at ~2.5 -> ~2.0 across 22-359 Hz -- "the signature of ~2-3 stacked LF high-pass
corners differing the same way". This script counts them.

Run: /opt/homebrew/bin/python3.11 analysis/clean_lf_corner_count.py
"""
import numpy as np

# ---- The model's OWN clean-path LF corners, cited per source --------------------------------
#
#   InputBuffer.h   : C1 (100 nF) into R2 (1 M, bias-to-VD) -- kR2/kC1, unchanged since the
#                      original schematic fit. First stage in the chain (base rate).
#   PedalChain.h     : C21Highpass -- C21 (100 nF, schematic-verified) into `r`, which
#                      FitParams::applyFitParams sets to `fit.c21R` (currently 130 k). This is
#                      the ONE corner in this list that was deliberately re-aimed AWAY from the
#                      ND captures, toward the hardware anchor (session 91,
#                      reference-sources.md Sec.5 rule 2) -- its current-vs-ND-matched values are
#                      exactly the 130k/12.2 Hz vs 220k/7.2 Hz pair session 167's "single corner"
#                      unit is built from.
#   MasterOut.h      : TWO corners, both ~0.72 Hz -- C36 (2.2uF) into the MASTER pot (100k, full
#                      CW) ahead of IC6_B, and C37 (2.2uF) into R46 (100k) after it. The LAST
#                      linear stage before the output jack.
#
# All four sit on the clean path: InputBuffer taps the clean signal at IC1_A (before the J201/
# clipper), and C21/C36/C37 are all POST-BLEND -- shared by clean and OD alike, and therefore
# present unconditionally in a BLEND=clean render (FitParams.h's own c21R note: "It is in the
# SHARED post-BLEND path (identical in all 30 captures)").
CORNERS_MODELLED = {
    "C1 (InputBuffer, R2=1M)":        1.0 / (2.0 * np.pi * 1.0e6 * 100.0e-9),
    "C21 (c21R, current=130k)":       1.0 / (2.0 * np.pi * 130.0e3 * 100.0e-9),
    "C36 (MasterOut input HPF)":      1.0 / (2.0 * np.pi * 100.0e3 * 2.2e-6),
    "C37 (MasterOut output HPF)":     1.0 / (2.0 * np.pi * 100.0e3 * 2.2e-6),
}

# The c21R "unit": phase(fc=12.2) - phase(fc=7.2) at 100n/130k vs 100n/220k -- the exact pair
# session 91's re-anchor moved between (FitParams.h c21R comment; reference-sources.md Sec.2).
FC_C21_ND_MATCHED = 1.0 / (2.0 * np.pi * 220.0e3 * 100.0e-9)   # session-28 ND fit, 7.2 Hz
FC_C21_HW_ANCHORED = 1.0 / (2.0 * np.pi * 130.0e3 * 100.0e-9)  # session-91 HW re-anchor, 12.2 Hz

# ---- A fifth, UNMODELLED corner -- flagged and never landed ---------------------------------
# circuit.md / Baxandall.h: C31 (2.2uF) couples the Baxandall stage's Vout to the LO-MID (IC5_D)
# input. The 2026-07-21 EQ-block build session flagged BOTH C21 and C31 as inter-stage coupling
# caps deferred at the Baxandall oracle's boundary, with an explicit carry-forward note to place
# BOTH during Phase-6/7 integration (docs/session-log.md, "EQ BLOCK... DONE" entry). C21 landed
# (PedalChain::C21Highpass). C31 did not -- grep for "C31"/"kC31" across src/dsp/*.h returns
# nothing outside Baxandall.h's own docstring. It is a genuine, still-open gap, NOT a decision.
#
# ⛔⛔ SUPERSEDED AT SESSION 177 BY GATE BG (analysis/c31_corner_gate.py) — READ THAT FIRST.
# Everything below this line about C31 is the s169 BRACKET, and it is wrong in both directions:
#   (1) THE CORNER IS COMPUTABLE, and the paragraph below saying it is not is what stopped s169
#       computing it. The two legs are not ALTERNATIVES, they load node Min TOGETHER, and the
#       R38 leg's far end is neither ground nor open — it runs through the pot ladder to the
#       stage's own DRIVEN output, whose DC gain is exactly -1. That inversion is a MILLER
#       factor: Zin_DC = 1/(1/R41 + (1-G0)/(R38+Rp+R39)) = 42.19k => fc = 1.715 Hz, with no fit
#       and no pot-/switch-position dependence.
#   (2) ⭐⭐ AND THE CORNER IS NOT THE STORY, so this whole file's framing does not reach it.
#       A corner-count assumes each cap sees a FIXED resistance. This one does not: |Zin| falls
#       42.2k -> 2.2k across the audio band (C32 shorts P3 to P1), so |Zin| and |1/(w*C31)| fall
#       TOGETHER and the divider never recovers. The true insertion is a broad PLATEAU reaching
#       -1.07 dB at a graded band centre, against the -0.02 dB the corner predicts there — 54x.
# ⇒ this file's closing sentence, "real, tiny, unactioned", is HALF RIGHT: it was real and
# unactioned, and it was not tiny. C31 was implemented at s177 (MidBand::setInputCap).
# ⚠ What DOES survive is this file's own subject — the PHASE count for item 13. A 1.715 Hz
# corner adds little phase over 22-359 Hz, so "the measured residual is NOT evidence of a
# ~30 Hz missing corner" stands, and item 13 stays closed. The magnitude was never in view.
#
# Its corner is NOT precisely computable without solving the 7-node MidBand input impedance at
# an arbitrary pot position, so this is bracketed rather than pinned. Node "Min" (circuit.md
# "LO-MID (IC5_D)") has TWO legs: R38 (2.2k) to P3 (the pot's upper lug -- NOT ground, it's the
# entry to the pot ladder + C32 + the rest of the 7-node network) and R41 (220k) straight to the
# (-) VIRTUAL GROUND (an ideal op-amp input held at 0 V by feedback -- a genuine low-Z AC ground).
# R38's far end is not a clean ground, so treating it as "R38 to ground" overstates the loading;
# R41 IS a clean ground path and is the more defensible single-resistor bound, even though it's
# 100x the other leg's raw value:
R38_TO_POT_NOT_GROUND = 2.2e3   # circuit.md R38 -- NOT used as the estimate; see comment above
R41_TO_VIRTUAL_GROUND = 220.0e3  # circuit.md R41 -- the genuine AC-ground path from "Min"
C31_UNMODELLED = 2.2e-6
FC_C31_UPPER_SEVERITY = 1.0 / (2.0 * np.pi * R38_TO_POT_NOT_GROUND * C31_UNMODELLED)   # too low-Z
FC_C31_ESTIMATE = 1.0 / (2.0 * np.pi * R41_TO_VIRTUAL_GROUND * C31_UNMODELLED)          # defensible


def hpf_phase_deg(f, fc):
    """First-order HPF phase, H(s) = sRC/(1+sRC): +90 deg at f<<fc, ->0 deg at f>>fc."""
    return np.degrees(np.arctan2(fc, f))


def main():
    print("Modelled clean-path LF corners (src/dsp/, closed-form, no captures):\n")
    for name, fc in CORNERS_MODELLED.items():
        print(f"  {name:30s} fc = {fc:8.4f} Hz")
    print(f"\n  c21R ND-matched (session-28, pre-91): fc = {FC_C21_ND_MATCHED:.4f} Hz  (~7.2 Hz)")
    print(f"  c21R HW-anchored (session-91, shipped): fc = {FC_C21_HW_ANCHORED:.4f} Hz  (~12.2 Hz)")
    print(f"\n  [gap] C31 (Baxandall->LO-MID, UNMODELLED) -- bracketed, not pinned:")
    print(f"    if loaded by R38 (2.2k, but R38 leads into the pot ladder, NOT ground): "
          f"fc ~= {FC_C31_UPPER_SEVERITY:.1f} Hz (too severe -- see below)")
    print(f"    if loaded by R41 (220k, the genuine virtual-ground leg -- more defensible): "
          f"fc ~= {FC_C31_ESTIMATE:.3f} Hz (negligible, same order as C36/C37)")

    freqs = np.geomspace(22.0, 359.0, 13)
    shift = hpf_phase_deg(freqs, FC_C21_HW_ANCHORED) - hpf_phase_deg(freqs, FC_C21_ND_MATCHED)

    total_modelled = sum(hpf_phase_deg(freqs, fc) for fc in CORNERS_MODELLED.values())
    others_only = sum(hpf_phase_deg(freqs, fc) for name, fc in CORNERS_MODELLED.items()
                       if "C21" not in name)
    total_with_c31_upper = total_modelled + hpf_phase_deg(freqs, FC_C31_UPPER_SEVERITY)

    print("\nTwo natural formulations, both closed-form from the corners above, no free parameter:")
    print("  (a) ALL 4 modelled corners' own phase, summed, over the c21R shift unit --")
    print("      an UPPER bound: assumes the pedal/ND capture is phase-flat at every one of")
    print("      these frequencies, i.e. that 100% of every corner's phase is 'residual'.")
    print("  (b) 1 + (the OTHER 3 corners' phase / the c21R shift) -- a LOWER-leaning read:")
    print("      counts c21R's own contribution as exactly 1 unit (its residual IS the shift,")
    print("      by construction), and asks how much MORE the other three corners add.")
    print()
    print(f"{'f (Hz)':>8} {'shift (deg)':>12} {'(a) all/shift':>15} {'(b) 1+other/shift':>19} "
          f"{'(a)+C31 upper':>14}")
    for f, s, tot, oth, totc31 in zip(freqs, shift, total_modelled, others_only, total_with_c31_upper):
        print(f"{f:8.2f} {s:12.4f} {tot/s:15.3f} {1.0 + oth/s:19.3f} {totc31/s:14.3f}")

    print("\nMeasured (session 167, docs/session-log.md SESSION 167 addendum, item 13),")
    print("for comparison -- NOT reproduced here (that pass was inline/ad-hoc and not saved as")
    print("a script): 2.53 / 2.50 / 2.50 / 2.43 / 2.42 / 2.37 / 2.38 / 2.34 / 2.31 / 2.27 / 2.21 /")
    print("2.09 / 2.01, same 22->359 Hz span, same qualitative shape (flat-ish, declining slowly")
    print("with frequency).")
    print("\nReading: (a) and (b) BRACKET the measured 2.0-2.5x (3.05-3.4 and 1.6-1.7 respectively)")
    print("-- consistent with '2-3 stacked LF corners of comparable order' without needing to know")
    print("ND's own LF-corner values (which set exactly where between (a) and (b) the truth sits).")
    print("The C31 gap argues AGAINST itself: at the R38 (upper-severity) estimate it would push")
    print("the multiple to ~8.5-9.6x, far above what is measured -- so either C31's real loading")
    print("is much closer to the R41 estimate (negligible), or the gap's audible impact is smaller")
    print("than a naive per-corner count suggests. Either way the measured residual is NOT")
    print("evidence of a ~30 Hz missing corner, and the gap is left exactly where W2 found it:")
    print("real, tiny, unactioned -- no DSP change owed (W2's own rule).")
    print()
    print("*** SUPERSEDED, SESSION 177 — run analysis/c31_corner_gate.py (GATE BG). ***")
    print("The corner IS computable: both legs load node Min together and the ladder leg lands on")
    print("a node driven at -1x, a MILLER factor, giving fc = 1.715 Hz with no fit and no pot- or")
    print("switch-position dependence. And the corner is NOT the story: |Zin| itself falls 42.2k")
    print("-> 2.2k across the band, so the true insertion is a broad PLATEAU reaching -1.07 dB at")
    print("a graded band centre where this framing predicts -0.02 dB. 'Tiny' was wrong; the PHASE")
    print("conclusion above (item 13) is unaffected, because a 1.7 Hz corner adds little phase.")


if __name__ == "__main__":
    main()
