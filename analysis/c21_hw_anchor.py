#!/usr/bin/env python3.11
"""Derive FitParams::c21R from the §2 HARDWARE anchor, instead of transcribing a flagged range.

Session 91. `CLAUDE.md` open-work item 1 has carried "c21R 220k -> ~130-150k" since session 71 with
the justification "hardware wants ~11-12 Hz where we sit at 7.2 Hz matched to ND". That range was
read off one frequency (20 Hz) by hand. `rebuild-targets-dont-transcribe`: this script encodes
`.claude/rules/reference-sources.md` §2's own table and FITS the corner over every LF anchor it
has, so the number is derived and the residual is visible.

WHAT IS BEING FITTED
--------------------
§2 is a third-party comparison sweep: two hardware pedals and the Neural DSP plugin, flat EQ, clean.
Its usable content is the HW - ND column.

⚠ THE TARGET IS `HW - MODEL`, NOT `HW - ND`. It is tempting to apply the §2 delta straight to our
chain, and that is what the flagged "~11-12 Hz = 130-150k" range effectively did — but it silently
assumes the model already sits ON ND at those bands. Measured over the 168 CLEAN rows of the
baseline report, it does not: relative to 200 Hz the model is already 0.40 dB BELOW ND at 20 Hz and
0.16 dB below at 30 Hz. So roughly a third of the move §2 asks for has already been made, by
constants fitted for other reasons, and applying the raw §2 delta would overshoot. This script
therefore subtracts the measured residual first (`decompose the deficit before changing constants`,
calibration doc §4) and fits the REMAINDER.

C21 is the only audible-band highpass in the shared post-BLEND path (everything else corners at
<= 1.6 Hz — FitParams::c21R), so that change is a single-pole move:

    delta(f) = 10*log10( (f^2 + fc0^2) / (f^2 + fc^2) )        fc0 = shipped corner (7.234 Hz)

and fc = 1 / (2*pi*R*C21), C21 = 100 nF schematic-verified. One free parameter, five targets, so the
fit is over-determined and its residual is the honest statement of how well a single pole can do.

⚠ WHAT THIS IS NOT. §2 is a PNG read of a 4 dB window. `reference-sources.md` §5 rule 3 forbids
running an optimiser against §3/§4 numbers; §2 is explicitly carved out ("the only section precise
enough to fit against") because it is gridlined and two independent hardware units agree — but a
0.1 dB difference between candidates here is not meaningful. The output rounds to E24.
"""
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matrix_grade as MG                              # noqa: E402

BASELINE = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                        "reports", "s90_baseline129_h1.json")

# The band the whole comparison is normalised on. §2 puts HW - ND at 0.00 dB at 200 Hz and reports a
# crossover at ~65 Hz, so anywhere in 65-200 Hz is a valid zero; 200 Hz is used because it is a §2
# row rather than an interpolation, and because the model's own residual is flat there (+0.17 to
# +0.22 dB across 63-254 Hz), so the choice moves the answer by <0.05 dB.
REF_HZ = 200.0

C21_F = 100.0e-9                  # schematic-verified, PedalChain::C21Highpass::kC21
R_SHIPPED = 220.0e3                  # FitParams::c21R, session-28 A2d

# reference-sources.md §2, "Reading (HW - ND)". Rebuilt from the table, not from its prose summary.
# (f_Hz, HW_dB, ND_dB). The rows §2 leaves as "—" (the two crossovers) are omitted; they are
# statements ABOUT this column, and are re-derived below as a check rather than fitted as data.
SECTION2 = [
    (15.0,   73.30, 74.72),
    (20.0,   73.70, 74.80),
    (30.0,   74.15, 74.90),
    (200.0,  75.40, 75.40),
    (900.0,  75.82, 75.51),   # §2 gives this row as "800-1k"; geometric centre
    (5000.0, 75.35, 75.74),
    (10000.0, 75.05, 75.86),
    (16000.0, 74.90, 76.02),
]

# Only the LF rows can be spoken to by a single pole at ~10 Hz — above ~200 Hz the delta(f) term is
# < 0.01 dB for any candidate in range, so the HF rows are a CONTROL (the fit must not want to move
# them), not fit data. Fitting them would let 5-16 kHz mid-emphasis vote on a bass corner.
LF_MAX_HZ = 300.0


def corner(r_ohm):
    return 1.0 / (2.0 * np.pi * r_ohm * C21_F)


def resistance(fc_hz):
    return 1.0 / (2.0 * np.pi * fc_hz * C21_F)


def delta_db(f, fc, fc0):
    """dB change in a first-order highpass response at f when its corner moves fc0 -> fc."""
    f = np.asarray(f, dtype=float)
    return 10.0 * np.log10((f ** 2 + fc0 ** 2) / (f ** 2 + fc ** 2))


def model_residual(path=BASELINE, method="h1band"):
    """-> (bands, median `plugin_db - pedal_db` per band over the CLEAN rows, n_rows).

    Signed, and NOT abs() — the sign is the whole point here, and `abs()` on a quantity whose sign
    IS observable is the session-33 trap. Median over rows rather than mean: the CLEAN pool spans
    every EQ setting, so a few deep-cut captures should not drag the LF shape.
    """
    bands, caps = MG.load(path)
    rows = []
    for f, c in caps.items():
        if MG.is_od(f):
            continue
        for _sw, fr in c["fr"].items():
            src = fr["methods"][method] if "methods" in fr else fr
            p, q = src["plugin_db"], src["pedal_db"]
            if max(p) < MG.SILENT_DB or max(q) < MG.SILENT_DB:
                continue
            rows.append(np.array(p) - np.array(q))
    if not rows:
        raise SystemExit("c21_hw_anchor: no CLEAN rows found — check the report path")
    return np.array(bands), np.median(np.array(rows), axis=0), len(rows)


def residual_at(bands, med, f_hz):
    """The model-vs-ND residual at f, referenced to REF_HZ, log-interpolated between bands."""
    lg = np.log10(bands)
    ref = float(np.interp(np.log10(REF_HZ), lg, med))
    return float(np.interp(np.log10(f_hz), lg, med)) - ref


def selftest():
    """Known answers, so a sign slip or a factor of 2pi cannot pass silently."""
    ok = True

    # KA-1: the shipped corner. 1/(2*pi*220k*100n).
    fc0 = corner(R_SHIPPED)
    ok &= abs(fc0 - 7.2343) < 1e-3
    print(f"  KA-1 shipped corner            {fc0:.4f} Hz   (FitParams says ~7.2)  "
          f"{'PASS' if abs(fc0 - 7.2343) < 1e-3 else 'FAIL'}")

    # KA-2: round trip R -> fc -> R.
    rt = resistance(corner(137.0e3))
    ok &= abs(rt - 137.0e3) < 1.0
    print(f"  KA-2 R->fc->R round trip       {rt/1e3:.3f} k                          "
          f"{'PASS' if abs(rt - 137.0e3) < 1.0 else 'FAIL'}")

    # KA-3: SIGN. Raising the corner must ATTENUATE the bass (negative delta), and moving it
    # nowhere must be exactly zero. A sign slip here is the whole finding inverted.
    d_up = delta_db(20.0, 14.0, 7.2343)
    d_none = delta_db(20.0, 7.2343, 7.2343)
    sign_ok = d_up < 0.0 and abs(d_none) < 1e-12
    ok &= sign_ok
    print(f"  KA-3 sign: fc up => cut         {d_up:+.3f} dB @20 Hz, no-move {d_none:+.1e}  "
          f"{'PASS' if sign_ok else 'FAIL'}")

    # KA-4: closed form. At f == fc the response is -3.0103 dB; at f == fc0 likewise. So moving
    # the corner from fc0 to fc changes the level AT fc0 by exactly -3.0103 - H(fc0 @ fc).
    fc = 14.0
    lhs = delta_db(fc0, fc, fc0)
    rhs = 20.0 * np.log10(fc0 / np.hypot(fc0, fc)) + 3.0103
    ok &= abs(lhs - rhs) < 1e-3
    print(f"  KA-4 closed form @f=fc0        {lhs:+.4f} vs {rhs:+.4f} dB              "
          f"{'PASS' if abs(lhs - rhs) < 1e-3 else 'FAIL'}")

    # KA-5: the HF rows really are unreachable, which is what justifies excluding them. The
    # largest |delta| any in-range candidate produces above LF_MAX_HZ must be negligible.
    worst = max(abs(delta_db(f, corner(100.0e3), fc0)) for f, _, _ in SECTION2 if f > LF_MAX_HZ)
    ok &= worst < 0.02
    print(f"  KA-5 HF rows unreachable       worst |delta| {worst:.4f} dB above {LF_MAX_HZ:.0f} Hz  "
          f"{'PASS' if worst < 0.02 else 'FAIL'}")

    # KA-6: the residual reader. Referenced to itself it must be exactly zero, and the CLEAN row
    # count must be the 168 the release gate reports — if this silently read the OD rows, or an
    # empty pool, the correction below would be garbage and would still print plausibly (s87).
    bands, med, n = model_residual()
    z = residual_at(bands, med, REF_HZ)
    r20 = residual_at(bands, med, 20.0)
    r6 = ok6 = (abs(z) < 1e-12 and n == 168 and -0.60 < r20 < -0.20)
    ok &= ok6
    print(f"  KA-6 residual reader           n={n} CLEAN rows, ref self {z:+.1e}, "
          f"20 Hz {r20:+.3f} dB   {'PASS' if ok6 else 'FAIL'}")
    del r6

    return ok


def verify(cand_path):
    """ACCEPTANCE CHECK: did the rendered candidate actually land on the §2 hardware target?

    The fit above predicts a move; this measures the one that happened. Reads the candidate's own
    CLEAN rows and asks whether `model - ND` now equals `HW - ND`. Run it on the render, never on
    the prediction — session 41's lesson is that a fit's own acceptance check failing is a blocker,
    and it can only fail if it is actually computed against the artefact.
    """
    bands_b, med_b, n_b = model_residual()
    bands_c, med_c, n_c = model_residual(cand_path)
    if n_b != n_c:
        print(f"  ! membership differs: baseline {n_b} CLEAN rows, candidate {n_c} "
              f"(`aggregate-moved-check-membership-first`) — the comparison below is NOT like-for-like")

    print(f"\n=== ACCEPTANCE: {os.path.basename(cand_path)} vs the §2 hardware target ===")
    print(f"    {n_c} CLEAN rows, referenced to {REF_HZ:g} Hz\n")
    print("      f Hz   HW-ND   model-ND before   after    remaining error   moved")
    rows = [(f, hw, nd) for f, hw, nd in SECTION2
            if f <= LF_MAX_HZ and f >= float(bands_b[0])]
    worst = 0.0
    for (fq, hw, nd) in rows:
        tgt = hw - nd
        before = residual_at(bands_b, med_b, fq)
        after = residual_at(bands_c, med_c, fq)
        err = after - tgt
        worst = max(worst, abs(err))
        print(f"    {fq:7.0f} {tgt:+7.2f}   {before:+13.2f}  {after:+7.2f}   {err:+13.2f}"
              f"   {after-before:+7.2f}")
    # A pure no-op render is the failure mode that reads as success: if the fit override never
    # reached OfflineRender, `after` == `before` at every band and the table above still prints.
    moved = max(abs(residual_at(bands_c, med_c, f) - residual_at(bands_b, med_b, f))
                for f, _, _ in rows)
    print(f"\n    worst remaining error {worst:.2f} dB   |   largest move {moved:.2f} dB")
    if moved < 0.01:
        print("    ⛔ THE CANDIDATE DID NOT MOVE — the --fit override did not reach the render "
              "(check the cache key hashes it). Do NOT read the gate as a result.")
    return worst, moved


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--verify", metavar="REPORT.json",
                    help="grade a rendered candidate against the §2 target (acceptance check)")
    a = ap.parse_args()

    print("=== C21 corner from the reference-sources.md §2 hardware anchor ===\n")
    print("SELF-TEST")
    if not selftest():
        raise SystemExit("self-test FAILED — do not read the numbers below")

    fc0 = corner(R_SHIPPED)
    bands, med, n_clean = model_residual()

    # §2's LF rows, each referenced to REF_HZ so HW, ND and the model share one zero. Only rows at
    # or above the lowest MEASURED band are usable: 15 Hz sits below the report's 20 Hz band, so
    # the model residual there would be an extrapolation, and §2's own 15 Hz row is its noisiest.
    lo_band = float(bands[0])
    lf = [(f, hw, nd) for f, hw, nd in SECTION2 if f <= LF_MAX_HZ]
    usable = [(f, hw, nd) for f, hw, nd in lf if f >= lo_band]
    dropped = [r[0] for r in lf if r[0] < lo_band]

    f = np.array([r[0] for r in usable])
    hw_nd = np.array([r[1] - r[2] for r in usable])                  # §2, already ref'd (200 Hz = 0)
    mdl_nd = np.array([residual_at(bands, med, fq) for fq in f])     # measured, ref'd to REF_HZ
    target = hw_nd - mdl_nd                                          # what is LEFT to do

    print(f"\nMODEL-vs-ND RESIDUAL, {n_clean} CLEAN rows of {os.path.basename(BASELINE)}, "
          f"referenced to {REF_HZ:g} Hz")
    if dropped:
        print(f"    dropped §2 row(s) below the lowest measured band ({lo_band:g} Hz): "
              f"{', '.join(f'{d:g} Hz' for d in dropped)}")

    # One free parameter; scan it densely and take the least-squares corner. A scan rather than a
    # solver so the objective's shape is visible and an edge-resting optimum cannot hide.
    grid = np.linspace(7.30, 40.0, 20000)
    sse = np.array([np.sum((delta_db(f, fc, fc0) - target) ** 2) for fc in grid])
    fc_ls = float(grid[int(np.argmin(sse))])
    interior = 0 < int(np.argmin(sse)) < len(grid) - 1

    print("\nTARGET DECOMPOSITION and the single-pole fit  (all dB, referenced to "
          f"{REF_HZ:g} Hz)")
    print(f"    shipped corner {fc0:.3f} Hz  (c21R = {R_SHIPPED/1e3:.0f}k)\n")
    print("      f Hz   HW-ND   model-ND    TARGET    fitted   resid")
    for j, (fq, hw, nd) in enumerate(usable):
        fit = float(delta_db(fq, fc_ls, fc0))
        print(f"    {fq:7.0f} {hw_nd[j]:+7.2f}   {mdl_nd[j]:+8.2f}  {target[j]:+8.2f}  "
              f"{fit:+8.2f}  {fit-target[j]:+6.2f}")
    resid = delta_db(f, fc_ls, fc0) - target
    print(f"\n    LS corner {fc_ls:.2f} Hz -> c21R = {resistance(fc_ls)/1e3:.1f}k"
          f"   RMS residual {np.sqrt(np.mean(resid**2)):.3f} dB"
          f"   interior optimum: {'YES' if interior else 'NO — EDGE-RESTING, do not ship'}")

    # Per-anchor corners: what each §2 row alone would ask for. Spread across these IS the
    # uncertainty, and it is larger than the difference between adjacent E24 values.
    print("\nWHAT EACH ANCHOR ALONE ASKS FOR (the spread is the real uncertainty)")
    for j, (fq, hw, nd) in enumerate(usable):
        t = float(target[j])
        if abs(t) < 1e-9:
            print(f"    {fq:7.0f} Hz  target {t:+.2f} dB  -> no move required (this row is the "
                  f"crossover, and pins the fit from above)")
            continue
        arg = (fq ** 2 + fc0 ** 2) / (10.0 ** (t / 10.0)) - fq ** 2
        if arg <= 0:
            print(f"    {fq:7.0f} Hz  target {t:+.2f} dB  -> UNREACHABLE by any corner")
            continue
        fci = np.sqrt(arg)
        print(f"    {fq:7.0f} Hz  target {t:+.2f} dB  -> fc {fci:6.2f} Hz  "
              f"= c21R {resistance(fci)/1e3:6.1f}k")

    # E24 quantisation. A resistor is a real part; quote what can be fitted.
    e24 = np.array([1.0, 1.1, 1.2, 1.3, 1.5, 1.6, 1.8, 2.0, 2.2, 2.4, 2.7, 3.0,
                    3.3, 3.6, 3.9, 4.3, 4.7, 5.1, 5.6, 6.2, 6.8, 7.5, 8.2, 9.1])
    cands = np.concatenate([e24 * 1e4, e24 * 1e5])
    r_ls = resistance(fc_ls)
    pick = float(cands[int(np.argmin(np.abs(np.log(cands / r_ls))))])
    print(f"\nNEAREST E24: {pick/1e3:.0f}k  -> corner {corner(pick):.2f} Hz"
          f"   (LS wants {r_ls/1e3:.1f}k / {fc_ls:.2f} Hz)")

    # What the change does to the GRADED bands — this is the cost side, and it lands entirely on
    # CLEAN, which is the one gate row currently MET. Print it beside the benefit, always.
    print("\nCONSEQUENCE AT THE GRADED 1/3-OCT BANDS (delta applied to BOTH clean and OD paths;\n"
          "C21 is post-BLEND, so this is a shift of the whole output, not of the OD path alone)")
    gbands = [25.0, 31.7, 40.0, 50.4, 63.5, 80.0, 100.8, 127.0, 160.0, 201.6]
    for r_try in sorted({pick, 150.0e3, 130.0e3}, reverse=True):
        fct = corner(r_try)
        row = "  ".join(f"{float(delta_db(b, fct, fc0)):+5.2f}" for b in gbands)
        print(f"    c21R {r_try/1e3:5.0f}k (fc {fct:5.2f} Hz): {row}")
    print("    bands (Hz):                    " +
          "  ".join(f"{b:5.0f}" for b in gbands))

    if a.verify:
        verify(a.verify)


if __name__ == "__main__":
    main()
