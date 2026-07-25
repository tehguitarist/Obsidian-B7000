#!/usr/bin/env python3.11
"""A2c-2 — which mid-stage HYPOTHESIS reproduces the pedal's measured curve?

Companion to mid_shape_fit.py.  That script established the finding; this one
tests competing structural explanations against it under one objective, and
reports the physical-plausibility evidence alongside the score so a fit cannot be
accepted on RMS alone (the session-5/6 + GAP #3b lesson).

OBJECTIVE.  Per band (LO-MID, HI-MID): the pedal's own stage contribution
(capture minus the all-flat `ref-clean`, in the pedal domain), MEAN-REMOVED over
the fit band rather than anchored at one frequency — the 5.12 kHz anchor
mid_range_probe.py uses is inside the HI-MID 3 kHz position's own skirt and
inverts that row's apparent shape.  Scored over both knob extremes and all three
switch positions at once, every parameter shared across a band's positions.

HYPOTHESES.
  H0  shipped              GAP #4's Rw + its [ENG] cap table (250 -> 22n)
  H1  Rw + free caps       keep Rw, let the switched cap table move freely
  H2  flat-leg + free caps R40/R41 scaled instead of Rw (limits range by lowering
                           the whole stage's authority, NOT by damping the
                           resonance, so it should not broaden)
  H3  cap PAIRS            C32 switched together with C33 at a fixed ratio
                           (constant-Q / constant-range by construction — the
                           alternative circuit.md parked and session 21 rejected
                           on range alone) + a flat-leg range limit
  H4  unconstrained        everything free; the ceiling, not a candidate

Usage:  python3.11 analysis/mid_shape_hypotheses.py [report.json]
"""
import contextlib
import io
import json
import os
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
with contextlib.redirect_stdout(io.StringIO()):
    from eq_reference import mid_stage_tf  # noqa: E402

from mid_shape_fit import BANDS, REPORT, SHIPPED, load, stage_shape  # noqa: E402

FIT_LO, FIT_HI = 100.0, 4100.0


def dbshape(bands, a, c33, c32, m, **kw):
    h = 20 * np.log10(np.abs(mid_stage_tf(bands, a, C33=c33, C32=c32, **kw)))
    return h - np.mean(h[m])


def curves(bands, c33, c32, m, ped_cut=None, **kw):
    """The stage at both pot extremes, mean-removed.

    Which pot end is "cut" is a sign convention the captures determine, not the
    oracle (mid_range_probe.py resolves it the same way).  It must NOT be decided
    from the mean-removed curve's own sign sum — that is ~0 for both by
    construction, which makes the choice arbitrary noise; pair against the pedal
    curve instead when one is supplied.
    """
    lo = dbshape(bands, 1e-6, c33, c32, m, **kw)
    hi = dbshape(bands, 1 - 1e-6, c33, c32, m, **kw)
    if ped_cut is not None:
        return (lo, hi) if np.dot(lo[m], ped_cut[m]) > np.dot(hi[m], ped_cut[m]) else (hi, lo)
    i = int(np.argmax(np.abs(lo)))          # unpaired: use the peak's sign
    return (lo, hi) if lo[i] < 0 else (hi, lo)


def band_targets(bands, by_file, band, m):
    c32nom, positions = BANDS[band]
    out = []
    for label, c33nom, f_cut, f_bst in positions:
        pc = stage_shape(bands, by_file, f_cut, "pedal_db")
        pb = stage_shape(bands, by_file, f_bst, "pedal_db")
        out.append((label, c33nom, pc - np.mean(pc[m]), pb - np.mean(pb[m])))
    return c32nom, out


def score(bands, c32nom, tgts, m, c33s, c32s, rw=0.0, rend=1.0, rflat=1.0, detail=False):
    """c33s/c32s: per-position lists. -> RMS dB (and per-position rows)."""
    kw = dict(R38=2.2e3 * rend, R39=2.2e3 * rend, R40=220e3 * rflat,
              R41=220e3 * rflat, Rw=rw)
    errs, rows = [], []
    for i, (label, _cn, pc, pb) in enumerate(tgts):
        cut, bst = curves(bands, c33s[i], c32s[i], m, ped_cut=pc, **kw)
        e = np.concatenate([cut[m] - pc[m], bst[m] - pb[m]])
        errs.append(e)
        rows.append((label, float(np.sqrt(np.mean(e ** 2)))))
    e = np.concatenate(errs)
    r = float(np.sqrt(np.mean(e ** 2)))
    return (r, rows) if detail else r


def fit(bands, c32nom, tgts, m, spec, x0, bounds):
    """spec(x, i) -> (c33_i, c32_i, rw, rend, rflat)."""
    def f(x):
        c33s, c32s, rw, rend, rflat = [], [], None, None, None
        for i in range(len(tgts)):
            c33, c32, rw, rend, rflat = spec(x, i, tgts)
            c33s.append(c33); c32s.append(c32)
        return score(bands, c32nom, tgts, m, c33s, c32s, rw, rend, rflat)
    r = minimize(f, x0, method="Nelder-Mead",
                 options=dict(maxiter=4000, xatol=1e-4, fatol=1e-4))
    # honour bounds by clipping and re-scoring (Nelder-Mead is unbounded)
    x = np.clip(r.x, [b[0] for b in bounds], [b[1] for b in bounds])
    return x, f(x)


def anchor(bands, curve, hz=5120.0):
    """Re-anchor a mean-removed curve at a band where the stage is ~flat, so the
    peak/bandwidth metrics below read against 0 dB. Diagnostic only — the fit
    objective is mean-removed and never uses this."""
    return curve - curve[int(np.argmin(np.abs(bands - hz)))]


def metrics(bands, curve, m):
    idx = np.arange(len(bands))[m]
    i = idx[int(np.argmax(np.abs(curve[m])))]
    pk, fc = curve[i], bands[i]
    half = abs(pk) / 2.0
    lo = hi = np.nan
    for j in range(i, 0, -1):
        if abs(curve[j]) <= half:
            lo = bands[j]; break
    for j in range(i, len(bands)):
        if abs(curve[j]) <= half:
            hi = bands[j]; break
    return pk, fc, (np.log2(hi / lo) if lo == lo and hi == hi else np.nan)


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    bands, by_file = load(args[0] if args else REPORT)
    m = (bands >= FIT_LO) & (bands <= FIT_HI)
    print(f"objective: RMS dB over {FIT_LO:.0f}-{FIT_HI:.0f} Hz, 3 switch positions x 2 knob "
          f"extremes,\n           pedal & model both MEAN-REMOVED over the fit band.\n")

    for band in ("LO-MID", "HI-MID"):
        c32nom, tgts = band_targets(bands, by_file, band, m)
        sh = SHIPPED[band]
        n = len(tgts)
        print(f"\n{'='*94}\n{band}   across-lug cap nominal {c32nom*1e9:g} nF, "
              f"shipped Rw {sh['rw']/1e3:g}k\n{'='*94}")

        print(f"\n  PEDAL vs SHIPPED MODEL, per position:")
        print(f"    {'pos':<6}{'ped pk':>8}{'@Hz':>7}{'ped BW':>8}  |"
              f"{'mdl pk':>8}{'@Hz':>7}{'mdl BW':>8}")
        for i, (label, _cn, pc, pb) in enumerate(tgts):
            ppk, pfc, pbw = metrics(bands, anchor(bands, pc), m)
            mc, _mb = curves(bands, sh["c33"][i], c32nom, m, ped_cut=pc, Rw=sh["rw"])
            mpk, mfc, mbw = metrics(bands, anchor(bands, mc), m)
            print(f"    {label:<6}{ppk:>8.1f}{pfc:>7.0f}{pbw:>8.2f}  |"
                  f"{mpk:>8.1f}{mfc:>7.0f}{mbw:>8.2f}")

        results = []

        # H0 shipped
        r0, rows0 = score(bands, c32nom, tgts, m, sh["c33"], [c32nom] * n,
                          rw=sh["rw"], detail=True)
        results.append(("H0 shipped (GAP #4)", r0, rows0, "Rw=%.0fk, [ENG] caps" % (sh["rw"] / 1e3)))

        # H1 keep Rw, free cap table
        def s1(x, i, t):
            return abs(x[i]) * t[i][1], c32nom, abs(x[n]), 1.0, 1.0
        x1, r1 = fit(bands, c32nom, tgts, m, s1, [1.0] * n + [sh["rw"]],
                     [(0.05, 20)] * n + [(0, 300e3)])
        _, rows1 = score(bands, c32nom, tgts, m, [abs(x1[i]) * tgts[i][1] for i in range(n)],
                         [c32nom] * n, rw=abs(x1[n]), detail=True)
        results.append(("H1 Rw + free caps", r1, rows1,
                        "Rw=%.0fk, caps x %s" % (abs(x1[n]) / 1e3,
                                                 ", ".join(f"{abs(v):.2f}" for v in x1[:n]))))

        # H2 flat-leg range limit + free cap table, no Rw
        def s2(x, i, t):
            return abs(x[i]) * t[i][1], c32nom, 0.0, 1.0, abs(x[n])
        x2, r2 = fit(bands, c32nom, tgts, m, s2, [1.0] * n + [0.35],
                     [(0.05, 20)] * n + [(0.01, 5)])
        _, rows2 = score(bands, c32nom, tgts, m, [abs(x2[i]) * tgts[i][1] for i in range(n)],
                         [c32nom] * n, rflat=abs(x2[n]), detail=True)
        results.append(("H2 R40/R41 + free caps", r2, rows2,
                        "R40/R41 x %.3f (=%.1fk), caps x %s"
                        % (abs(x2[n]), 220 * abs(x2[n]),
                           ", ".join(f"{abs(v):.2f}" for v in x2[:n]))))

        # H3 cap PAIRS (C32 tracks C33 at a fixed ratio) + flat-leg limit
        def s3(x, i, t):
            c33 = abs(x[i]) * t[i][1]
            return c33, c33 * abs(x[n]), 0.0, 1.0, abs(x[n + 1])
        x3, r3 = fit(bands, c32nom, tgts, m, s3, [1.0] * n + [c32nom / tgts[0][1], 0.35],
                     [(0.05, 20)] * n + [(0.01, 50), (0.01, 5)])
        _, rows3 = score(bands, c32nom, tgts, m,
                         [abs(x3[i]) * tgts[i][1] for i in range(n)],
                         [abs(x3[i]) * tgts[i][1] * abs(x3[n]) for i in range(n)],
                         rflat=abs(x3[n + 1]), detail=True)
        results.append(("H3 cap PAIRS + R40/R41", r3, rows3,
                        "C32/C33 = %.2f (switched), R40/R41 x %.3f (=%.1fk), C33 x %s"
                        % (abs(x3[n]), abs(x3[n + 1]), 220 * abs(x3[n + 1]),
                           ", ".join(f"{abs(v):.2f}" for v in x3[:n]))))

        # H4 unconstrained ceiling
        def s4(x, i, t):
            return abs(x[i]) * t[i][1], c32nom * abs(x[n]), abs(x[n + 1]), abs(x[n + 2]), abs(x[n + 3])
        x4, r4 = fit(bands, c32nom, tgts, m, s4, [1.0] * n + [1.0, 1e3, 1.0, 1.0],
                     [(0.05, 20)] * n + [(0.05, 50), (0, 300e3), (0.1, 100), (0.01, 5)])
        results.append(("H4 unconstrained", r4, None,
                        "C32 x %.2f, Rw=%.0fk, R38/39 x %.2f, R40/41 x %.3f"
                        % (abs(x4[n]), abs(x4[n + 1]) / 1e3, abs(x4[n + 2]), abs(x4[n + 3]))))

        print(f"\n  {'hypothesis':<26}{'RMS dB':>8}   per-position RMS")
        print("  " + "-" * 90)
        for name, r, rows, note in results:
            pp = ("   " + "  ".join(f"{lab}:{v:.2f}" for lab, v in rows)) if rows else ""
            print(f"  {name:<26}{r:>8.2f}{pp}")
            print(f"  {'':<26}        {note}")
    print("\nNOTE: RMS alone is not acceptance — check the fitted values are physical, that the")
    print("objective has an interior minimum, and that a band's positions stay differentiated.")


if __name__ == "__main__":
    main()
