#!/usr/bin/env python3.11
"""GAP #4 — fit the mid stage's range-limiting element to the captures.

Runs AFTER `mid_range_probe.py` has established that (a) the plugin reproduces the
modelled network to ~0.5 dB, so the error is in the NETWORK not the DSP, and (b) the
pedal's shortfall is a CEILING (pedal/model ratio rises 0.49 -> 0.93 toward the small
caps), not a constant scale — so it is a real range-limiting element, not knob
under-travel.

`schematic-checker` (2026-07-25) returned TOPOLOGY CONFIRMED FAITHFUL: MidBand.h
matches circuit.md node for node, and the full R1-R54 BOM census leaves no spare
resistor for an unmodelled element. Per the pre-registered decision tree in
docs/phase9-validation.md §4 GAP #4, we therefore fit the element to the capture
(dsp.md "fit the corner"; the whole mid-cap table is [ENG]-computed anyway).

Target = the boost-to-cut SPAN per 1/3-oct band at all six switch positions at once
(matched-pair differential; see mid_range_probe.py). Every parameter is SHARED across
all six positions — a per-position fudge would be meaningless.

    python3.11 analysis/mid_range_fit.py            # fit + candidate table
    python3.11 analysis/mid_range_fit.py --curves   # + per-band curves for the winner
"""
import sys
import os
import io
import contextlib

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):  # eq_reference prints a diagnostic dump on import
    from mid_range_probe import (POSITIONS, REPORT, load, span, summarise,  # noqa: E402
                                 oracle_span)

FIT_LO, FIT_HI = 160.0, 4100.0

# Free parameters, all SHARED across the six positions.
#   rw       series R in the wiper/cap leg (ohms)     — the position-independent limiter
#   rend     R38/R39/R42/R43 scale (x 2k2)
#   rflat    R40/R41/R44/R45 scale (x 220k)
#   c32s     C32/C34 across-lug cap scale
#   c33lo    LO-MID switched-cap table scale
#   c33hi    HI-MID switched-cap table scale
P_NAMES = ["rw", "rend", "rflat", "c32s", "c33lo", "c33hi"]
P_NOMINAL = dict(rw=0.0, rend=1.0, rflat=1.0, c32s=1.0, c33lo=1.0, c33hi=1.0)


def targets(bands, by_file):
    out = []
    for label, c33, c32, f_lo, f_hi in POSITIONS:
        if f_lo not in by_file or f_hi not in by_file:
            continue
        sp, _, _, _ = summarise(bands, span(by_file, f_lo, f_hi, "pedal_db"), label)
        out.append((label, c33, c32, label.startswith("LO"), sp))
    return out


def model_span(bands, c33, c32, is_lo, p):
    return oracle_span(bands,
                       c33 * (p["c33lo"] if is_lo else p["c33hi"]),
                       c32 * p["c32s"],
                       rw=p["rw"],
                       r38=2.2e3 * p["rend"], r39=2.2e3 * p["rend"],
                       r40=220e3 * p["rflat"], r41=220e3 * p["rflat"])


def cost(bands, tgts, p):
    m = (bands >= FIT_LO) & (bands <= FIT_HI)
    errs = []
    for label, c33, c32, is_lo, ped in tgts:
        sp, _, _, _ = summarise(bands, model_span(bands, c33, c32, is_lo, p), label)
        errs.append(sp[m] - ped[m])
    return float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))


def fit(bands, tgts, free, x0=None):
    """Optimise the named `free` params; everything else stays nominal."""
    base = dict(P_NOMINAL)
    if not free:
        return base, cost(bands, tgts, base)

    # optimise in log space (all params are positive scales / resistances)
    start = np.array([np.log(max(x0[k] if x0 else _seed(k), 1e-9)) for k in free])

    def f(x):
        p = dict(base)
        for k, v in zip(free, np.exp(x)):
            p[k] = v
        # keep the search physical: no negative/absurd values
        if p["rw"] > 2e6 or p["rend"] > 200 or p["rflat"] > 50:
            return 1e3
        return cost(bands, tgts, p)

    best = None
    for jitter in (0.0, 0.6, -0.6):
        r = minimize(f, start + jitter, method="Nelder-Mead",
                     options=dict(maxiter=4000, xatol=1e-4, fatol=1e-5))
        if best is None or r.fun < best.fun:
            best = r
    p = dict(base)
    for k, v in zip(free, np.exp(best.x)):
        p[k] = v
    return p, float(best.fun)


def _seed(k):
    return {"rw": 47e3}.get(k, 1.0)


def show(p):
    return (f"rw={p['rw']/1e3:7.2f}k  rend={p['rend']:5.2f} (R38={2.2*p['rend']:6.2f}k)  "
            f"rflat={p['rflat']:5.2f} (R40={220*p['rflat']:6.1f}k)  "
            f"c32s={p['c32s']:5.2f}  c33lo={p['c33lo']:5.2f}  c33hi={p['c33hi']:5.2f}")


def main():
    bands, by_file = load(REPORT)
    tgts = targets(bands, by_file)

    print("GAP #4 — fitting the mid-stage range limiter to the captures")
    print(f"target: boost-to-cut span, {len(tgts)} switch positions x "
          f"{int(((bands >= FIT_LO) & (bands <= FIT_HI)).sum())} bands "
          f"({FIT_LO:.0f}-{FIT_HI:.0f} Hz)\n")

    trials = [
        ("shipped (all nominal)", []),
        ("A. wiper-leg series R only", ["rw"]),
        ("B. R38/R39 end resistors only", ["rend"]),
        ("C. R40/R41 flat legs only", ["rflat"]),
        ("D. Rw + LO/HI cap-table scale", ["rw", "c33lo", "c33hi"]),
        ("E. Rw + R38/R39", ["rw", "rend"]),
        ("F. Rw + R38/R39 + cap table", ["rw", "rend", "c33lo", "c33hi"]),
        ("G. everything free", P_NAMES),
    ]
    results = []
    for name, free in trials:
        p, c = fit(bands, tgts, free)
        results.append((name, free, p, c))
        print(f"  {name:<32} RMS {c:6.3f} dB   {show(p)}")

    print("\nPer-position check (span peak dB @ Hz) for the leading candidates:")
    lead = sorted(results, key=lambda r: r[3])[:3]
    hdr = f"{'position':<26}{'pedal':>13}"
    for name, *_ in lead:
        hdr += f"{name.split('.')[0]:>13}"
    print(hdr)
    for label, c33, c32, is_lo, ped in tgts:
        _, pp, pf, _ = summarise(bands, ped, label)
        row = f"{label:<26}{pp:>7.1f}@{pf:>5.0f}"
        for name, free, p, c in lead:
            _, mp, mf, _ = summarise(bands, model_span(bands, c33, c32, is_lo, p), label)
            row += f"{mp:>7.1f}@{mf:>5.0f}"
        print(row)

    if "--curves" in sys.argv:
        name, free, p, c = lead[0]
        print(f"\n\nPer-band span curves — winner: {name} (RMS {c:.3f})")
        m = (bands >= FIT_LO) & (bands <= FIT_HI)
        for label, c33, c32, is_lo, ped in tgts:
            sp, _, _, _ = summarise(bands, model_span(bands, c33, c32, is_lo, p), label)
            print(f"\n  {label}")
            print("    Hz    " + " ".join(f"{b:>7.0f}" for b in bands[m]))
            print("    pedal " + " ".join(f"{v:>7.1f}" for v in ped[m]))
            print("    fit   " + " ".join(f"{v:>7.1f}" for v in sp[m]))
            print("    err   " + " ".join(f"{v:>7.1f}" for v in (sp[m] - ped[m])))
    return results


if __name__ == "__main__":
    main()


# =============================================================================
# Refined fit — the excess span correlates with the ABSOLUTE size of the switched
# cap (47n +26.6 dB, 15n +15.2, 10n +17.7, 3n3 +11.2, 2n2 +2.8, 820p +1.5), which
# is the signature of a SERIES RESISTANCE in the wiper leg: negligible while Xc is
# large (small caps), dominant once the cap is a short (large caps). So Rw is the
# right element. The residual after Rw is a CENTRE error confined to LO-MID "250"
# (model 229 Hz vs pedal 320 Hz), which no range element can fix — that is a cap
# value, and the [ENG] cap table was computed, never measured, so each position's
# cap is a legitimate free parameter pinned by its own measured centre.
# =============================================================================

def fit2(bands, tgts, free_rw, free_caps, x0=None):
    """free_rw: subset of ['rwlo','rwhi']; free_caps: list of position indices."""
    idx_free = {i: n for n, i in enumerate(free_caps)}
    n_rw = len(free_rw)

    def unpack(x):
        v = np.exp(x)
        rw = {k: v[i] for i, k in enumerate(free_rw)}
        caps = {i: v[n_rw + j] for i, j in idx_free.items()}
        return rw, caps

    def build(rw, caps, i, c33, c32, is_lo):
        r = rw.get("rwlo" if is_lo else "rwhi", rw.get("rwlo", rw.get("rwhi", 0.0)))
        return oracle_span(bands, c33 * caps.get(i, 1.0), c32, rw=r)

    m = (bands >= FIT_LO) & (bands <= FIT_HI)

    def f(x):
        rw, caps = unpack(x)
        if any(v > 1e6 for v in rw.values()) or any(v > 5 or v < 0.05 for v in caps.values()):
            return 1e3
        errs = []
        for i, (label, c33, c32, is_lo, ped) in enumerate(tgts):
            sp, _, _, _ = summarise(bands, build(rw, caps, i, c33, c32, is_lo), label)
            errs.append(sp[m] - ped[m])
        return float(np.sqrt(np.mean(np.concatenate(errs) ** 2)))

    start = np.log(np.array([40e3] * n_rw + [1.0] * len(free_caps)))
    best = None
    for j in (0.0, 0.4, -0.4):
        r = minimize(f, start + j, method="Nelder-Mead",
                     options=dict(maxiter=8000, maxfev=8000, xatol=1e-5, fatol=1e-6))
        if best is None or r.fun < best.fun:
            best = r
    rw, caps = unpack(best.x)
    return rw, caps, float(best.fun), build


def main2():
    bands, by_file = load(REPORT)
    tgts = targets(bands, by_file)
    print("\n\n=== REFINED FIT: wiper-leg series R (+ per-position cap values) ===\n")
    for name, free_rw, free_caps in [
        ("Rw shared (one R, both bands)", ["rwlo"], []),
        ("Rw per band (LO/HI separate)", ["rwlo", "rwhi"], []),
        ("Rw per band + LO-250 cap", ["rwlo", "rwhi"], [0]),
        ("Rw per band + all 6 caps", ["rwlo", "rwhi"], [0, 1, 2, 3, 4, 5]),
    ]:
        rw, caps, c, build = fit2(bands, tgts, free_rw, free_caps)
        rws = "  ".join(f"{k}={v/1e3:.1f}k" for k, v in rw.items())
        cs = "  ".join(f"C[{i}]x{v:.2f}" for i, v in sorted(caps.items()))
        print(f"  {name:<32} RMS {c:6.3f}   {rws}   {cs}")
        if free_caps == [0, 1, 2, 3, 4, 5]:
            print(f"\n  Winner per-position (span peak dB @ Hz):")
            print(f"    {'position':<26}{'pedal':>13}{'fit':>13}   fitted cap")
            for i, (label, c33, c32, is_lo, ped) in enumerate(tgts):
                _, pp, pf, _ = summarise(bands, ped, label)
                sp, mp, mf, _ = summarise(bands, build(rw, caps, i, c33, c32, is_lo), label)
                newc = c33 * caps.get(i, 1.0)
                unit = "n" if newc >= 1e-9 else "p"
                sc = newc * (1e9 if unit == "n" else 1e12)
                print(f"    {label:<26}{pp:>7.1f}@{pf:>5.0f}{mp:>7.1f}@{mf:>5.0f}   "
                      f"{c33*1e9:6.3f}n -> {sc:6.3f}{unit}")


if __name__ == "__main__" and "--refine" in sys.argv:
    main2()
