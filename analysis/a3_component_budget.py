#!/usr/bin/env python3.11
"""a3_component_budget -- split A3's shape curve into its components, and settle how
much of the flat floor is the bleed level `beta` rather than a real OD deficit.

WHY
---
`a3_shape_gate` states A3 as one curve, `20 log10 s(f)` -- the dB by which the
model's OD path must grow at each band. But that curve is at least three
superposed things (session 47 item 2):

    C1  a broadband floor              ~ +2.7 dB, flat
    C2  a low-mid rise 64 -> 508 Hz    ~ +6 dB on top of the floor
    C3  a steep LF rise below 40 Hz    ~ 9.5 dB/oct, steeper than 1st order

Every A3 candidate since session 34 has been ONE element asked to carry more than
one of them, and each time the element bought one component by overshooting
another: `clipC15` at 1.5 nF (session 36/37), the `btC17` f0-pair (session 47/49).
So the budget has to be written down BEFORE the next element is fitted.

THE BETA QUESTION, AND WHY IT COMES FIRST
-----------------------------------------
`s` is not measured in isolation -- it is solved jointly with the pedal's bleed
level beta, which `a3_shape_gate.fit_beta` re-fits for every candidate:

    t_d(b) = beta + 20 log10 | 1 + s(b) . mu_d(b) . e^(i.theta(b)) |

Raising beta by 1 dB lowers the s the fit needs. So a PURELY FLAT component of the
curve is partly degenerate with beta, and "the model's OD is 2.7 dB too weak
everywhere" and "the pedal's bleed is 2.7 dB hotter than we think" are the same
data. If beta is only loosely identified, C1 is not a real finding and no element
should be fitted to it. If beta is tightly identified, C1 is real and needs its own
(broadband-gain) lever rather than being dumped onto a frequency-shaping element.

This tool answers that by sweeping beta and reporting BOTH the resulting curve and
how fast the joint fit degrades -- i.e. beta's identifiability interval, measured
rather than assumed.

⚠ Reads build/a3_dec_drv*.csv at whatever state they are in. Verify them first
(`a3_shape_gate.py --selfcheck`) -- session 45 found them silently stale at an old
kInputRef, and every A3 tool reads them.

Usage:  python3.11 analysis/a3_component_budget.py
"""
import argparse
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_phase_solve as ps                                          # noqa: E402
import a3_shape_gate as sg                                           # noqa: E402

FLOOR_BAND = [50, 64]              # where the curve bottoms out -> C1
C2_BANDS = [101, 127, 160, 202, 254, 403, 508]
C3_BANDS = [20, 25, 32]


def solve_at(pedal, model, beta):
    """s_db per CORE/INFO band at a FIXED beta, plus the total fit residual."""
    rows, tot = {}, 0.0
    for b in sg.BETA_BANDS:
        mu = np.array([model[d][b][0] for d, _ in ps.DRIVES])
        t = np.array(pedal[b])
        (_, cost, s), _ = ps.fit_band(t, mu, beta)
        rows[b] = 20.0 * math.log10(s)
        tot += cost
    return rows, tot


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--csv-prefix", default="build/a3_dec_drv")
    args = ap.parse_args()

    model = ps.load_model([d for d, _ in ps.DRIVES], args.csv_prefix)
    pedal = ps.load_pedal(args.sweep)

    # ---- 1. beta sweep: the curve AND the fit residual -----------------------
    # ⚠ Wide enough that the optimum is INTERIOR. A truncated range puts the
    # minimum on the sweep edge and then reports a one-point "identifiability
    # interval" that is an artefact of the range, not a property of the data --
    # the first draft of this tool did exactly that (edge at -17.00 while
    # a3_shape_gate.fit_beta reports -16.80). Assert interiority below.
    lo_b, hi_b, step_b = -20.0, -14.0, 0.25
    betas = [round(lo_b + step_b * i, 2)
             for i in range(int(round((hi_b - lo_b) / step_b)) + 1)]
    out = {}
    for b in betas:
        rows, tot = solve_at(pedal, model, b)
        score = math.sqrt(np.mean([rows[k] ** 2 for k in sg.CORE]))
        out[b] = (rows, tot, score)

    best_beta = min(out, key=lambda k: out[k][1])
    best_cost = out[best_beta][1]
    if best_beta in (betas[0], betas[-1]):
        sys.exit("beta optimum %.2f is ON the sweep edge [%.2f, %.2f] -- widen the "
                 "range; the identifiability interval below would be an artefact."
                 % (best_beta, betas[0], betas[-1]))
    # Identifiability: how far can beta move before the JOINT fit residual
    # degrades appreciably? Expressed as the interval within +5 % of the optimum,
    # and (tighter, more familiar) within +0.25 dB rms per band.
    n = len(sg.BETA_BANDS) * len(ps.DRIVES)
    rms_of = lambda c: math.sqrt(c / n)
    # ⚠ The identifiability criterion is the MEASUREMENT FLOOR, not a round number.
    # The pedal's own take-to-take repeatability is 0.144 dB rms (shape-normalised,
    # phase9-validation.md §1), so a beta whose joint fit residual sits under that
    # is indistinguishable from the optimum ON THIS DATA and a beta above it is
    # excluded by it. A looser threshold (the first draft used +0.25 dB) widens the
    # interval to +-1.6 dB and makes the LF component look unidentified when the
    # captures do in fact pin it.
    CAPTURE_FLOOR_DB = 0.144
    ok_floor = [b for b in betas if rms_of(out[b][1]) <= CAPTURE_FLOOR_DB]
    ok25 = [b for b in betas if rms_of(out[b][1]) <= rms_of(best_cost) + 0.25]

    print("=== 1. beta sweep (model bleed ships at -16.93 dB) ===")
    print("%7s %9s %8s %8s   %s" % ("beta", "fit rms", "score", "floor",
                                    "20log10 s at 20 / 50 / 254 / 508 Hz"))
    for b in betas:
        rows, tot, score = out[b]
        floor = min(rows[k] for k in sg.CORE)
        mark = "  <- fit_beta optimum" if b == best_beta else ""
        print("%7.2f %9.4f %8.3f %+8.2f   %+6.2f %+6.2f %+6.2f %+6.2f%s"
              % (b, rms_of(tot), score, floor,
                 rows[20], rows[50], rows[254], rows[508], mark))

    print("\nfit_beta optimum              = %.2f dB   (rms %.4f dB)"
          % (best_beta, rms_of(best_cost)))
    print("identified (rms <= %.3f dB)  = [%.2f, %.2f] dB   <- the capture floor"
          % (CAPTURE_FLOOR_DB, min(ok_floor), max(ok_floor)))
    print("loose (rms <= opt + 0.25 dB)  = [%.2f, %.2f] dB" % (min(ok25), max(ok25)))
    print("model's own bleed             = -16.93 dB")

    # How robust is each component across beta's IDENTIFIED interval? A component
    # that swings across it is not a measurement yet and must be fitted jointly
    # with beta, never against this curve as if it were fixed (session 33 item 3).
    print("\ncomponent robustness across the identified beta interval:")
    for b, label in ((20, "C3  20 Hz "), (50, "C1  50 Hz "), (254, "C2 254 Hz "),
                     (508, "C2 508 Hz ")):
        vals = [out[k][0][b] for k in ok_floor]
        print("  %s  %+6.2f .. %+6.2f dB   (span %.2f)"
              % (label, min(vals), max(vals), max(vals) - min(vals)))

    # ---- 2. what beta CAN and CANNOT remove ---------------------------------
    # The honest test: at the most generous beta the data still permits, how much
    # of the flat floor survives?
    hi_beta = max(ok25)
    rows_hi = out[hi_beta][0]
    rows_best = out[best_beta][0]
    print("\n=== 2. how much of the flat floor is beta? ===")
    print("At the fit optimum beta=%.2f the curve's floor is %+.2f dB."
          % (best_beta, min(rows_best[k] for k in sg.CORE)))
    print("At the most generous beta the data permits (%.2f), it is %+.2f dB."
          % (hi_beta, min(rows_hi[k] for k in sg.CORE)))
    print("=> beta can account for at most %.2f dB of the floor; %+.2f dB is a real"
          % (min(rows_best[k] for k in sg.CORE) - min(rows_hi[k] for k in sg.CORE),
             min(rows_hi[k] for k in sg.CORE)))
    print("   broadband OD-level deficit that NO bleed level explains.")

    # ---- 3. the component budget -------------------------------------------
    r = rows_best
    c1 = float(np.mean([r[b] for b in FLOOR_BAND]))
    c2 = float(np.mean([r[b] for b in C2_BANDS])) - c1
    c3 = r[20] - c1
    print("\n=== 3. component budget at the fitted beta (dB of |OD| lift needed) ===")
    print("  C1  broadband floor   (mean of %s Hz)      = %+6.2f dB" % (FLOOR_BAND, c1))
    print("  C2  low-mid rise      (mean of 101-508 Hz) = %+6.2f dB on top of C1" % c2)
    print("  C3  LF rise           (20 Hz)              = %+6.2f dB on top of C1" % c3)
    print("      C3 slope 32->20 Hz                     = %6.2f dB/oct"
          % ((r[20] - r[32]) / math.log2(32.0 / 20.0)))
    print("\n  full curve:")
    for b in sg.CORE:
        bar = "#" * int(round(max(r[b], 0) * 3))
        print("   %6d %+7.2f  %s" % (b, r[b], bar))

    # ---- 4. what each component costs if left unfixed ------------------------
    print("\n=== 4. score if each component alone were fixed perfectly ===")
    base = math.sqrt(np.mean([r[b] ** 2 for b in sg.CORE]))
    print("  as it stands                          %6.3f dB" % base)
    for name, fix in (("C1 only (subtract the floor)",
                       {b: r[b] - c1 for b in sg.CORE}),
                      ("C2 only (flatten 101-508 to C1)",
                       {b: (c1 if b in C2_BANDS else r[b]) for b in sg.CORE}),
                      ("C3 only (flatten 20-32 to C1)",
                       {b: (c1 if b in C3_BANDS else r[b]) for b in sg.CORE}),
                      ("C1+C2", {b: (0.0 if b in C2_BANDS else r[b] - c1) for b in sg.CORE}),
                      ("C1+C2+C3",
                       {b: (0.0 if b in C2_BANDS + C3_BANDS else r[b] - c1) for b in sg.CORE})):
        s = math.sqrt(np.mean([fix[b] ** 2 for b in sg.CORE]))
        print("  %-37s %6.3f dB" % (name, s))
    return 0


if __name__ == "__main__":
    sys.exit(main())
