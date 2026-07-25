#!/usr/bin/env python3.11
"""A2c-3 — PER-SWITCH-POSITION mid-stage fit (user-authorised 2026-07-26).

A2c-2 (session 26) fitted the mid stage's SHAPE with every parameter SHARED across
a band's three switch positions, and capped there: peak-frequency error 3.1 % mean,
but a residual 1.31x bandwidth (the plugin's peaks are still too broad) that is
structural under the shared-parameter constraint.  One wiper-leg R must serve all
three positions, and it is the element that trades range against Q, so it cannot be
right at three different cap values at once.

The user has now authorised per-knob / per-switch-position fitting for this stage
(same posture as clipK / clipC11: a user-authorised departure from a shared,
schematic-plausible element when the capture disagrees).  That unlocks the
per-position family A2c-2 rejected on principle.

WHAT IS FITTED, AND THE PHYSICAL READING OF EACH FAMILY
  F0  baseline            session-26 shipped: per-position C33, ONE Rw per band
  F1  + per-position Rw    the mid-frequency selector is 2-pole and switches a
                           series R in the wiper leg alongside the cap.  This is
                           the cheapest per-position story and it targets Q
                           directly, which is exactly the residual.
  F2  + per-position C32   the selector also switches the ACROSS-LUG cap (C32/C34)
                           — i.e. a 2-pole switch on the other element instead.
  F3  F1 + F2              both, per position (3 dof per position).
  F4  F3 + per-position R40/R41 scale — the ceiling, not a candidate; run only to
                           show how much is left above F3.

THE OBJECTIVE is the same one A2c-2 settled on: the pedal's own stage contribution
(capture minus the all-flat `ref-clean`, differenced inside one domain so the rest
of the chain and the report's per-capture gain match cancel), MEAN-REMOVED over the
fit band rather than anchored at one frequency — the 5.12 kHz anchor sits inside the
HI-MID 3 kHz position's own skirt and inverts that row's apparent shape.

Unlike A2c-2 this also uses the INTERIOR KNOB POINTS where they exist (the two
default switch positions have 0930 / 1430 captures as well as the extremes), so a
per-position fit cannot buy the extremes by wrecking mid-travel — the GAP #4 pot-law
lesson, applied per position.

Usage:
    python3.11 analysis/mid_perpos_fit.py [report.json]           # fit all families
    python3.11 analysis/mid_perpos_fit.py --scan                  # interior-minimum
                                                                  #   scans for F1/F3
    python3.11 analysis/mid_perpos_fit.py --band 63 8000          # widen the fit band
"""
import contextlib
import io
import os
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):   # eq_reference prints on import
    from eq_reference import mid_stage_tf         # noqa: E402

from mid_shape_fit import REPORT, load, stage_shape  # noqa: E402

FIT_LO, FIT_HI = 100.0, 4100.0

E12 = [1.0, 1.2, 1.5, 1.8, 2.2, 2.7, 3.3, 3.9, 4.7, 5.6, 6.8, 8.2]

# band -> (across-lug cap nominal, shipped Rw, [(label, shipped C33, [(a, file), ...])])
# a = electrical pot fraction = 1 - knob (OfflineRender inverts the EQ pots);
# knob 0700 = 0.0 -> a = 1 (CUT), 1700 = 1.0 -> a = 0 (BOOST), 0930 -> 0.75, 1430 -> 0.25.
BANDS = {
    "LO-MID": (22.0e-9, 22.0e3, [
        ("250", 15.0e-9, [
            (1.00, "lomidfreq-250_lomid-0700_base-clean.wav"),
            (0.00, "lomidfreq-250_lomid-1700_gain-n12_base-clean.wav")]),
        ("500", 6.8e-9, [
            (1.00, "lomid-0700_base-clean.wav"),
            (0.75, "lomid-0930_base-clean.wav"),
            (0.25, "lomid-1430_gain-n12_base-clean.wav"),
            (0.00, "lomid-1700_gain-n12_base-clean.wav")]),
        ("1k", 1.8e-9, [
            (1.00, "lomidfreq-1k_lomid-0700_base-clean.wav"),
            (0.00, "lomidfreq-1k_lomid-1700_gain-n12_base-clean.wav")]),
    ]),
    "HI-MID": (6.8e-9, 18.0e3, [
        ("750", 10.0e-9, [
            (1.00, "himidfreq-750_himid-0700_base-clean.wav"),
            (0.00, "himidfreq-750_himid-1700_gain-n12_base-clean.wav")]),
        ("1.5k", 2.7e-9, [
            (1.00, "himid-0700_base-clean.wav"),
            (0.75, "himid-0930_base-clean.wav"),
            (0.25, "himid-1430_gain-n12_base-clean.wav"),
            (0.00, "himid-1700_gain-n12_base-clean.wav")]),
        ("3k", 0.68e-9, [
            (1.00, "himidfreq-3k_himid-0700_base-clean.wav"),
            (0.00, "himidfreq-3k_himid-1700_gain-n12_base-clean.wav")]),
    ]),
}


def e12(v):
    """Nearest E12 value (any decade), preserving sign/magnitude."""
    d = 10.0 ** np.floor(np.log10(v))
    cand = np.array([m * dd for dd in (d / 10, d, d * 10) for m in E12])
    return float(cand[int(np.argmin(np.abs(np.log(cand / v))))])


def targets(bands, by_file, band, m):
    """[(label, shipped_c33, [(a, mean-removed pedal curve), ...]), ...]"""
    c32nom, rw0, positions = BANDS[band]
    out = []
    for label, c33ship, caps in positions:
        curves = []
        for a, fn in caps:
            if fn not in by_file:
                raise SystemExit(f"missing capture in report: {fn}")
            p = stage_shape(bands, by_file, fn, "pedal_db")
            curves.append((a, p - np.mean(p[m])))
        out.append((label, c33ship, curves))
    return c32nom, rw0, out


def model(bands, a, m, c33, c32, rw, rflat=1.0):
    h = 20 * np.log10(np.abs(mid_stage_tf(bands, a, C33=c33, C32=c32, Rw=rw,
                                          R40=220e3 * rflat, R41=220e3 * rflat)))
    return h - np.mean(h[m])


def pos_rms(bands, m, curves, c33, c32, rw, rflat=1.0):
    e = [model(bands, a, m, c33, c32, rw, rflat)[m] - ped[m] for a, ped in curves]
    e = np.concatenate(e)
    return float(np.sqrt(np.mean(e ** 2)))


def fit_pos(bands, m, curves, x0, free, bounds):
    """Fit one position. `free` names which of (c33, c32, rw, rflat) vary; the rest
    are held at x0. Search is in log space so every value stays positive."""
    keys = ("c33", "c32", "rw", "rflat")
    base = dict(zip(keys, x0))

    def unpack(z):
        p = dict(base)
        for k, v in zip(free, z):
            p[k] = float(np.exp(v))
        return p

    def f(z):
        p = unpack(z)
        return pos_rms(bands, m, curves, p["c33"], p["c32"], p["rw"], p["rflat"])

    z0 = np.log([max(base[k], 1e-12) for k in free])
    r = minimize(f, z0, method="Nelder-Mead",
                 options=dict(maxiter=6000, maxfev=6000, xatol=1e-5, fatol=1e-6))
    # Nelder-Mead is unbounded: clip to the physical box and re-score.
    z = np.clip(r.x, [np.log(bounds[k][0]) for k in free],
                [np.log(bounds[k][1]) for k in free])
    return unpack(z), f(z)


# Rw is allowed 0.1 ohm .. 1 Mohm; a value pinned at either end is a red flag, not a fit.
BOUNDS = dict(c33=(1e-12, 1e-6), c32=(1e-12, 1e-6), rw=(1e-1, 1e6), rflat=(0.05, 20.0))

FAMILIES = [
    ("F0 baseline (session 26)", ()),
    ("F1 + per-position Rw", ("c33", "rw")),
    ("F2 + per-position C32", ("c33", "c32")),
    ("F3 per-position C33+C32+Rw", ("c33", "c32", "rw")),
    ("F4 F3 + per-position R40/R41", ("c33", "c32", "rw", "rflat")),
]


def fit_pair(bands, m, tgts, c32nom, rw0, per_pos_rw=False):
    """F5/F6 — the CAP-PAIR family.

    F2's per-position optimum comes out at a near-constant C33/C32 ratio at every
    switch position, in BOTH bands. That is not a per-position fudge at all: it is
    one 2-POLE selector swapping a scaled cap PAIR, which is circuit.md's own parked
    alternative for this stage. Constraining the ratio to be shared across a band's
    three positions makes the stage's SHAPE (Q, and hence boost/cut range) identical
    at every position and lets only the centre frequency move — which is exactly what
    the captures say the pedal does (~+-12 dB at every position, the GAP #4 finding).

    Fitted per band: one C33 per position, ONE C32/C33 ratio, and Rw (shared, or per
    position when per_pos_rw). Session 26 tested a cap pair and rejected it, but with
    Rw dropped and a flat-leg limiter substituted; the pair only works WITH Rw.
    """
    n = len(tgts)

    def unpack(z):
        c33 = np.exp(z[:n])
        ratio = np.exp(z[n])
        rw = np.exp(z[n + 1:])
        return c33, ratio, (rw if per_pos_rw else np.repeat(rw[0], n))

    def rows_for(z):
        c33, ratio, rw = unpack(z)
        return [pos_rms(bands, m, tgts[i][2], c33[i], c33[i] * ratio, rw[i]) for i in range(n)]

    def f(z):
        r = rows_for(z)
        return float(np.sqrt(np.mean(np.square(r))))

    z0 = np.concatenate([np.log([t[1] for t in tgts]),
                         [np.log(c32nom / tgts[0][1])],
                         np.log([rw0] * (n if per_pos_rw else 1))])
    r = minimize(f, z0, method="Nelder-Mead",
                 options=dict(maxiter=20000, maxfev=20000, xatol=1e-5, fatol=1e-6))
    c33, ratio, rw = unpack(r.x)
    return c33, ratio, rw, rows_for(r.x)


def run(bands, by_file, m, do_scan):
    chosen = {}
    for band in ("LO-MID", "HI-MID"):
        c32nom, rw0, tgts = targets(bands, by_file, band, m)
        print(f"\n{'=' * 96}\n{band}   C32 nominal {c32nom * 1e9:g} nF, shipped Rw {rw0 / 1e3:g}k"
              f"   ({len(tgts)} switch positions)\n{'=' * 96}")
        print(f"  {'family':<30}{'mean':>7}" + "".join(f"{lab:>8}" for lab, _c, _q in tgts))

        results = {}
        for name, free in FAMILIES:
            rows, params = [], []
            for label, c33ship, curves in tgts:
                x0 = (c33ship, c32nom, rw0, 1.0)
                if not free:
                    p = dict(zip(("c33", "c32", "rw", "rflat"), x0))
                    r = pos_rms(bands, m, curves, *x0)
                else:
                    p, r = fit_pos(bands, m, curves, x0, free, BOUNDS)
                rows.append(r)
                params.append(p)
            results[name] = (rows, params)
            print(f"  {name:<30}{np.mean(rows):>7.3f}" + "".join(f"{v:>8.3f}" for v in rows))

        for name, free in FAMILIES:
            if not free:
                continue
            rows, params = results[name]
            print(f"\n  {name} fitted values:")
            for (label, c33ship, _q), p in zip(tgts, params):
                bits = [f"C33 {p['c33'] * 1e9:7.3f} nF (was {c33ship * 1e9:g})"]
                if "c32" in free:
                    bits.append(f"C32 {p['c32'] * 1e9:7.3f} nF (nom {c32nom * 1e9:g})")
                if "rw" in free:
                    bits.append(f"Rw {p['rw'] / 1e3:8.2f} k (was {rw0 / 1e3:g})")
                if "rflat" in free:
                    bits.append(f"R40/41 x{p['rflat']:.2f}")
                print(f"    {label:<6} " + "  ".join(bits))

        # --- the cap-PAIR families -----------------------------------------
        for name, ppr in (("F5 cap PAIR, shared Rw", False),
                          ("F6 cap PAIR, per-pos Rw", True)):
            c33, ratio, rw, rows = fit_pair(bands, m, tgts, c32nom, rw0, per_pos_rw=ppr)
            results[name] = (rows, [dict(c33=c33[i], c32=c33[i] * ratio, rw=rw[i], rflat=1.0)
                                    for i in range(len(tgts))])
            print(f"  {name:<30}{np.mean(rows):>7.3f}"
                  + "".join(f"{v:>8.3f}" for v in rows))
            print(f"  {'':<30}   C32/C33 = {ratio:.3f}  ->  "
                  + ", ".join(f"{lab} C33 {c * 1e9:.3g}n / C32 {c * ratio * 1e9:.3g}n"
                              for (lab, _s, _q), c in zip(tgts, c33))
                  + f";  Rw {', '.join(f'{v / 1e3:.1f}k' for v in rw)}")

        chosen[band] = (c32nom, rw0, tgts, results)

        if do_scan:
            scans(bands, m, band, tgts, results)
    return chosen


def scans(bands, m, band, tgts, results):
    """Interior-minimum check: sweep each fitted parameter of F3 about its optimum,
    holding the others. A monotone objective = a 'make it see less' degeneracy, which
    is what killed the session-5/6 clipper fits and the GAP #3b C13 candidate."""
    _rows, params = results["F3 per-position C33+C32+Rw"]
    print(f"\n  INTERIOR-MINIMUM SCANS ({band}, F3) — each parameter about its optimum,"
          f"\n  others held. A minimum in the middle of the row is the pass condition.")
    for (label, _cs, curves), p in zip(tgts, params):
        print(f"\n    {label}:")
        for key in ("c33", "c32", "rw"):
            v0 = p[key]
            mults = [0.5, 0.7, 0.85, 1.0, 1.2, 1.45, 2.0]
            cells = []
            for k in mults:
                q = dict(p)
                q[key] = v0 * k
                cells.append(pos_rms(bands, m, curves, q["c33"], q["c32"], q["rw"], q["rflat"]))
            best = int(np.argmin(cells))
            unit = "k" if key == "rw" else "nF"
            sc = 1e-3 if key == "rw" else 1e9
            mark = "INTERIOR" if 0 < best < len(mults) - 1 else "!! ON EDGE"
            print(f"      {key:<6}{v0 * sc:9.3f}{unit:<3} " +
                  " ".join(f"{c:5.2f}" for c in cells) + f"   {mark}")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    global FIT_LO, FIT_HI
    if "--band" in sys.argv:
        i = sys.argv.index("--band")
        FIT_LO, FIT_HI = float(sys.argv[i + 1]), float(sys.argv[i + 2])
        args = [a for a in args if a not in (sys.argv[i + 1], sys.argv[i + 2])]
    path = args[0] if args else REPORT
    bands, by_file = load(path)
    m = (bands >= FIT_LO) & (bands <= FIT_HI)
    print(f"report: {path}")
    print(f"objective: RMS dB over {FIT_LO:.0f}-{FIT_HI:.0f} Hz, pedal & model mean-removed,")
    print("           per switch position, over every captured knob point for that position.")
    run(bands, by_file, m, "--scan" in sys.argv)


if __name__ == "__main__":
    main()
