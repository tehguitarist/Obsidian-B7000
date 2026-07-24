#!/usr/bin/env python3.11
"""GAP #4 final fit — the mid stage's wiper-leg series resistance (midWiperR).

EVIDENCE CHAIN (each step is a separate measurement, see docs/phase9-validation.md §4):
 1. The plugin reproduces the modelled network's boost-to-cut span to ~0.5 dB at all
    six switch positions -> the error is in the NETWORK MODEL, not the DSP.
 2. `schematic-checker` (2026-07-25): TOPOLOGY CONFIRMED FAITHFUL. MidBand.h matches
    circuit.md node for node; the full R1-R54 BOM census leaves no spare resistor.
 3. The rail clamp is bit-inert on these clean captures (0.0000 dB vs railEnabled=0),
    so this is not op-amp rail compression.
 4. NOT knob under-travel: pedal/model ratio RISES 0.49 -> 0.93 toward the small caps,
    i.e. a ceiling the small-cap positions never reach, not a constant scale.
 5. The excess tracks the ABSOLUTE size of the switched cap (47n +26.6 dB ... 820p
    +1.5 dB) -> a series R in the wiper leg: negligible while Xc dominates (small
    caps), dominant once the cap is a short (large caps).
 6. The measured POT LAW confirms the same thing from the other direction: at 25%/75%
    travel the model already matches the pedal to ~1 dB; the entire error is in the
    last of the travel, symmetrically at both ends — which is exactly where the pot's
    own series resistance stops masking anything in the wiper leg.

So the fitted element is a series R between the wiper and the switched cap, one per
band. Per the pre-registered decision tree (§4 GAP #4) this is fit to the CAPTURE, not
derived — same posture as c21R, trebleLadderDampR and the rail voltages.

Objective = 6 extreme-position span curves + the 4-point pot law at the two default
positions (the pot-law terms stop the fit buying the extremes by wrecking mid-travel).

    python3.11 analysis/mid_range_final_fit.py
"""
import sys
import os
import io
import contextlib

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from mid_range_probe import POSITIONS, REPORT, load, span, summarise, oracle_span
    from eq_reference import mid_stage_tf

FIT_LO, FIT_HI = 160.0, 4100.0
REF = "ref-clean.wav"

# 4-point pot law, default switch positions. knob -> electrical a is INVERTED
# (readParams' 1-x): knob 0 = full CUT = a->1.
POT_LAW = [
    ("LO-MID 500Hz", 10.0e-9, 22.0e-9, 508.0, [
        (0.00, "lomid-0700_base-clean.wav"), (0.25, "lomid-0930_base-clean.wav"),
        (0.75, "lomid-1430_gain-n12_base-clean.wav"), (1.00, "lomid-1700_gain-n12_base-clean.wav")]),
    ("HI-MID 1.5kHz", 3.3e-9, 6.8e-9, 1613.0, [
        (0.00, "himid-0700_base-clean.wav"), (0.25, "himid-0930_base-clean.wav"),
        (0.75, "himid-1430_gain-n12_base-clean.wav"), (1.00, "himid-1700_gain-n12_base-clean.wav")]),
]


def main():
    bands, by = load(REPORT)
    i5 = int(np.argmin(np.abs(bands - 5120.0)))
    m = (bands >= FIT_LO) & (bands <= FIT_HI)

    # --- targets -----------------------------------------------------------
    spans = []
    for label, c33, c32, f_lo, f_hi in POSITIONS:
        ped, _, _, _ = summarise(bands, span(by, f_lo, f_hi, "pedal_db"), label)
        spans.append((label, c33, c32, label.startswith("LO"), ped))

    def rel(f, key):
        c = (np.array(by[f]["fr"]["sweep_clean"][key], float)
             - np.array(by[REF]["fr"]["sweep_clean"][key], float))
        return c - c[i5]

    laws = []
    for label, c33, c32, pk, files in POT_LAW:
        ib = int(np.argmin(np.abs(bands - pk)))
        pts = [(knob, rel(f, "pedal_db")[ib]) for knob, f in files]
        laws.append((label, c33, c32, ib, label.startswith("LO"), pts))

    def law_model(a, c33, c32, rw, ib):
        h = mid_stage_tf(bands, a, C33=c33, C32=c32, Rw=rw)
        h0 = mid_stage_tf(bands, 0.5, C33=c33, C32=c32, Rw=rw)
        d = 20 * np.log10(np.abs(h)) - 20 * np.log10(np.abs(h0))
        return (d - d[i5])[ib]

    def cost(rwlo, rwhi, detail=False):
        e = []
        for label, c33, c32, is_lo, ped in spans:
            sp, _, _, _ = summarise(bands, oracle_span(bands, c33, c32,
                                                       rw=rwlo if is_lo else rwhi), label)
            e.append(sp[m] - ped[m])
        span_rms = float(np.sqrt(np.mean(np.concatenate(e) ** 2)))
        le = []
        for label, c33, c32, ib, is_lo, pts in laws:
            rw = rwlo if is_lo else rwhi
            for knob, ped_db in pts:
                a = 1.0 - knob
                a = 1e-6 if a <= 0 else (1 - 1e-6 if a >= 1 else a)
                le.append(law_model(a, c33, c32, rw, ib) - ped_db)
        law_rms = float(np.sqrt(np.mean(np.array(le) ** 2)))
        return (span_rms, law_rms) if detail else np.hypot(span_rms, law_rms)

    def f(x):
        rwlo, rwhi = np.exp(x)
        if max(rwlo, rwhi) > 1e6:
            return 1e3
        return cost(rwlo, rwhi)

    best = None
    for j in (0.0, 0.5, -0.5):
        r = minimize(f, np.log([30e3, 20e3]) + j, method="Nelder-Mead",
                     options=dict(maxiter=6000, xatol=1e-5, fatol=1e-6))
        if best is None or r.fun < best.fun:
            best = r
    rwlo, rwhi = np.exp(best.x)

    print("GAP #4 FINAL FIT — wiper-leg series resistance\n")
    print(f"{'candidate':<28}{'span RMS':>10}{'law RMS':>10}{'combined':>10}")
    for name, a, b in [("shipped (Rw = 0)", 0.0, 0.0),
                       ("fitted", rwlo, rwhi),
                       ("fitted, rounded to E12", 33e3, 22e3),
                       ("single shared 27k", 27e3, 27e3)]:
        s, l = cost(a, b, detail=True)
        print(f"{name:<28}{s:>10.2f}{l:>10.2f}{np.hypot(s, l):>10.2f}"
              f"   (LO {a/1e3:.1f}k, HI {b/1e3:.1f}k)")

    print(f"\nfitted: midWiperR LO-MID = {rwlo/1e3:.1f}k   HI-MID = {rwhi/1e3:.1f}k")

    for rl, rh, tag in [(0.0, 0.0, "shipped"), (33e3, 22e3, "E12 33k/22k")]:
        print(f"\n--- span peak, {tag} ---")
        print(f"  {'position':<26}{'pedal':>13}{'model':>13}")
        for label, c33, c32, is_lo, ped in spans:
            _, pp, pf, _ = summarise(bands, ped, label)
            sp, mp, mf, _ = summarise(bands, oracle_span(bands, c33, c32,
                                                         rw=rl if is_lo else rh), label)
            print(f"  {label:<26}{pp:>7.1f}@{pf:>5.0f}{mp:>7.1f}@{mf:>5.0f}")

    print("\n--- pot law at the peak band, E12 33k/22k ---")
    print(f"  {'band':<16}{'knob':>6}{'pedal':>9}{'shipped':>9}{'fitted':>9}")
    for label, c33, c32, ib, is_lo, pts in laws:
        for knob, ped_db in pts:
            a = 1.0 - knob
            a = 1e-6 if a <= 0 else (1 - 1e-6 if a >= 1 else a)
            s0 = law_model(a, c33, c32, 0.0, ib)
            s1 = law_model(a, c33, c32, 33e3 if is_lo else 22e3, ib)
            print(f"  {label:<16}{knob:>6.2f}{ped_db:>9.1f}{s0:>9.1f}{s1:>9.1f}")


if __name__ == "__main__":
    main()


# =============================================================================
# Joint fit — Rw sets the RANGE, the switched cap sets the CENTRE.
# Rw alone drags every peak centre DOWN (LO-MID 500Hz: 508 -> 403 Hz), which
# regresses positions whose centre was already right. The two knobs are close to
# orthogonal (Rw = height, C = centre), so fit them together. Refitting the caps
# is legitimate: circuit.md tags the whole table [ENG-caps] — computed from the
# p.3 f-vs-C fit, never schematic-verified, and the captures now contradict it
# (the measured LO-MID "250" centre is 320 Hz, not the computed 229 Hz).
# =============================================================================

def joint():
    bands, by = load(REPORT)
    i5 = int(np.argmin(np.abs(bands - 5120.0)))
    m = (bands >= FIT_LO) & (bands <= FIT_HI)

    spans = []
    for label, c33, c32, f_lo, f_hi in POSITIONS:
        ped, _, _, _ = summarise(bands, span(by, f_lo, f_hi, "pedal_db"), label)
        spans.append((label, c33, c32, label.startswith("LO"), ped))

    def rel(f, key):
        c = (np.array(by[f]["fr"]["sweep_clean"][key], float)
             - np.array(by[REF]["fr"]["sweep_clean"][key], float))
        return c - c[i5]

    laws = []
    for label, c33, c32, pk, files in POT_LAW:
        ib = int(np.argmin(np.abs(bands - pk)))
        laws.append((label, c33, c32, ib, label.startswith("LO"),
                     [(k, rel(f, "pedal_db")[ib]) for k, f in files]))
    # which POSITIONS index each pot-law band corresponds to (500Hz -> 1, 1.5k -> 4)
    law_pos = [1, 4]

    def cost(x, detail=False):
        v = np.exp(x)
        rw = {True: v[0], False: v[1]}
        cs = v[2:]
        e = []
        for i, (label, c33, c32, is_lo, ped) in enumerate(spans):
            sp, _, _, _ = summarise(bands, oracle_span(bands, c33 * cs[i], c32,
                                                       rw=rw[is_lo]), label)
            e.append(sp[m] - ped[m])
        span_rms = float(np.sqrt(np.mean(np.concatenate(e) ** 2)))
        le = []
        for j, (label, c33, c32, ib, is_lo, pts) in enumerate(laws):
            c = c33 * cs[law_pos[j]]
            h0 = mid_stage_tf(bands, 0.5, C33=c, C32=c32, Rw=rw[is_lo])
            for knob, ped_db in pts:
                a = 1.0 - knob
                a = 1e-6 if a <= 0 else (1 - 1e-6 if a >= 1 else a)
                h = mid_stage_tf(bands, a, C33=c, C32=c32, Rw=rw[is_lo])
                d = 20 * np.log10(np.abs(h)) - 20 * np.log10(np.abs(h0))
                le.append((d - d[i5])[ib] - ped_db)
        law_rms = float(np.sqrt(np.mean(np.array(le) ** 2)))
        return (span_rms, law_rms) if detail else np.hypot(span_rms, law_rms)

    def f(x):
        v = np.exp(x)
        if max(v[0], v[1]) > 1e6 or np.any(v[2:] > 4) or np.any(v[2:] < 0.15):
            return 1e3
        return cost(x)

    best = None
    for j in (0.0, 0.4, -0.4):
        r = minimize(f, np.log(np.array([33e3, 22e3] + [1.0] * 6)) + j,
                     method="Nelder-Mead",
                     options=dict(maxiter=20000, maxfev=20000, xatol=1e-6, fatol=1e-7))
        if best is None or r.fun < best.fun:
            best = r
    v = np.exp(best.x)
    s, l = cost(best.x, detail=True)
    print("\n\n=== JOINT FIT: Rw (range) + switched caps (centre) ===")
    print(f"  span RMS {s:.2f}   law RMS {l:.2f}   combined {np.hypot(s, l):.2f}")
    print(f"  midWiperR: LO-MID {v[0]/1e3:.1f}k   HI-MID {v[1]/1e3:.1f}k")
    print(f"\n  {'position':<26}{'pedal':>13}{'joint fit':>13}   cap: [ENG] -> fitted")
    for i, (label, c33, c32, is_lo, ped) in enumerate(spans):
        _, pp, pf, _ = summarise(bands, ped, label)
        sp, mp, mf, _ = summarise(bands, oracle_span(bands, c33 * v[2 + i], c32,
                                                     rw=v[0] if is_lo else v[1]), label)
        nc = c33 * v[2 + i]
        print(f"  {label:<26}{pp:>7.1f}@{pf:>5.0f}{mp:>7.1f}@{mf:>5.0f}   "
              f"{c33*1e9:7.3f}n -> {nc*1e9:7.3f}n  (x{v[2+i]:.2f})")
    return v


if __name__ == "__main__" and "--joint" in sys.argv:
    joint()
