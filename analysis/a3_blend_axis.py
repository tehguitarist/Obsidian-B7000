#!/usr/bin/env python3.11
"""a3_blend_axis -- A3 measured on the BLEND axis, where the mixing law is LINEAR
and PARAMETER-FREE (session 51, Phase 9 / A3).

WHY THIS AXIS
-------------
Every A3 instrument to date infers the pedal's OD phasor by inverting a NONLINEAR
equation along the DRIVE ladder:

    t_d = beta * |1 + s . mu_d . e^(i.theta)|        d = 1..5      (a3_phase_solve)

That solve is bimodal in s, needs a grid on both axes, is only as identified as the
cancellation is deep, and consumes the MODEL's own mu_d shape -- so `s(f)`
(`a3_shape_gate`, the curve every A3 decision is now made on) inherits any error in
how the model responds to DRIVE. Sessions 33 and 47 both had to correct published
conclusions for exactly that reason.

The BLEND axis has none of those properties and had never been used to solve:

  * BLEND sits AFTER everything, so sweeping it changes NEITHER the OD phasor nor
    the clean phasor -- both are literally constant across the five captures.
  * The mixing is LINEAR in the knob. From LevelBlend.h the wiper feeds high-Z
    IC5_A, so the whole 100k track carries one current INDEPENDENT of B and the
    wiper is a plain tap on it. Normalising by the B = 0 capture (blend-0700, which
    IS the clean tap) gives

        t(B) = | beta(B) + B . G |,     beta(B) = 1 - B.(1 - b0)

    with b0 the clean-bleed coefficient at BLEND max and G = a0.Vo/Vc the complex OD
    contribution. a0, L and the LEVEL taper never appear -- a0 folds into G and
    cancels when pedal is divided by model.
  * Squaring (c = 1 - b0):

        t(B)^2 = 1 + B . 2(Q - c) + B^2 . (P - 2Qc + c^2),   P = |G|^2, Q = |G|cos(theta)

    i.e. a QUADRATIC IN B WITH UNIT INTERCEPT. Four non-zero BLEND points determine
    its two coefficients by ordinary least squares -- closed form, no grid, no
    branch to jump -- and leave TWO SPARE EQUATIONS PER BAND that test the mixing
    law itself instead of assuming it.

  ⭐ Harmonics do NOT break the law, which is what lets it be applied to a
  distorting path at all: every OD harmonic is multiplied by the same B and the
  clean tap contributes none, so band ENERGY keeps the same form with P absorbing
  the harmonic power. Confirmed empirically -- the model control below fits to
  0.0000 dB on a render whose OD path is clipping hard.

⚠⚠ WHAT THIS AXIS CANNOT DO: MEASURE THE BLEED LEVEL. Three unknowns (c, P, Q) map
onto only TWO quadratic coefficients, so (c, P, Q) is one-dimensionally DEGENERATE
and every c fits equally well. Verified, not assumed: freeing c on the MODEL's own
render -- where the true value is 0.14239 -- returns c consistent with b0 = 0.886 at
a residual of 0.0002 dB. So this tool takes b0 from the model and CANNOT be used to
challenge beta; beta remains the drive axis's business (session 34 item 2 bounds it
from monotonicity, session 50 puts it at -16.75 dB in [-17.25, -16.50]).

RESULTS THIS TOOL ESTABLISHED (session 51)
  1. ✅ LevelBlend's mixing law is CORRECT. Once the BLEND pot's own taper
     conformity is allowed, the pedal obeys it to worst 0.08 dB per band over
     20 Hz - 1.6 kHz, BELOW the 0.144 dB take-to-take floor. The BLEND/LEVEL
     network is not A3's cause -- a hypothesis that would otherwise have been live.
  2. ⭐ The pedal's BLEND taper is measurably non-linear: effective B =
     0.212 / 0.482 / 0.739 at knob 0.25 / 0.50 / 0.75. Ordinary conformity error,
     but it means the INTERIOR blend captures must not be used with nominal B.
     Nothing prior is invalidated: sessions 8/29 used only the ENDPOINTS, and both
     endpoints are taper-immune (at B = 1 the wiper IS pin3, so beta(1) = b0
     whatever the taper does; B = 0 is the normaliser).
  3. s_blend(f) = an independent estimate of the A3 defect curve -- see the table.

Usage:
    python3.11 analysis/a3_blend_axis.py --selftest
    python3.11 analysis/a3_blend_axis.py --validate
    python3.11 analysis/a3_blend_axis.py [--sweep sweep_drv_-18] [--fixed-taper]
"""
import argparse
import cmath
import json
import math
import os
import sys

import numpy as np

REPORT = "analysis/reports/comprehensive_data.json"
DECOMPOSE_CSV = "build/a3_dec_drv0.5.csv"        # drive noon = _REF_OD, the blend group's state

# (BLEND knob, capture). captures.py::_clock_to_x: 0700->0, 0930->0.25, 1200->0.5,
# 1430->0.75; ref-od IS blend = 1.0 (_REF_OD).
BLENDS = [
    (0.00, "blend-0700_base-od.wav"),
    (0.25, "blend-0930_base-od.wav"),
    (0.50, "blend-1200_base-od.wav"),
    (0.75, "blend-1430_base-od.wav"),
    (1.00, "ref-od.wav"),
]

LEVEL_KNOB, LEVEL_TAPER_EXP = 0.5, 2.25          # FitParams::levelTaperExp (shipped)
TAKE_FLOOR_DB = 0.144                            # measured pedal take-to-take (session 24)
FIT_HI_HZ = 1700.0                               # bands above this must not set shared params


def model_b0():
    """The model's bleed coefficient at BLEND max: b0 = 1/(1/(1-L) + 1/L + 1)."""
    L = LEVEL_KNOB ** LEVEL_TAPER_EXP
    return 1.0 / (1.0 / (1.0 - L) + 1.0 / L + 1.0)


def quad_fit(t, Bint):
    """Least-squares (k1, k2) for t(B)^2 = 1 + k1.B + k2.B^2 over the 4 non-zero points.

    Returns (k1, k2, per_point_dB_residual, infeasible_flag). `infeasible` is set when
    the fitted quadratic goes non-positive at a data point -- near a deep null the dB
    residual then blows up and must be reported as infeasible, not as a huge number.
    """
    B = np.asarray(list(Bint) + [1.0], dtype=float)
    tt = np.asarray(t[1:], dtype=float)
    A = np.vstack([B, B * B]).T
    k = np.linalg.lstsq(A, tt * tt - 1.0, rcond=None)[0]
    pred = 1.0 + A @ k
    bad = bool(np.any(pred <= 0.0))
    res = [20.0 * math.log10(math.sqrt(p) / x) if p > 0 else float("nan")
           for p, x in zip(pred, tt)]
    return float(k[0]), float(k[1]), res, bad


def unpack(k1, k2, b0):
    """(k1, k2) -> (r, theta, cos_raw) at a GIVEN bleed level. See the degeneracy note."""
    c = 1.0 - b0
    Q = k1 / 2.0 + c
    P = k2 + c * k1 + c * c
    r = math.sqrt(max(P, 1e-30))
    cos_raw = Q / r if P > 0 else 9e9
    return r, math.acos(max(-1.0, min(1.0, Q / r if P > 0 else 1.0))), cos_raw


def load_totals(key, sweep):
    """{band: [t(B) linear, normalised to the B=0 capture]} from the report.

    ⚠ `plugin_db` has the report's PER-CAPTURE gain-match baked in
    (`comprehensive_report.fr_at_bands`: `plugin_db = H_ren + gain_db`) and MUST have
    it un-applied before any cross-capture combination, or every BLEND point carries
    its own scalar, the law fails by ~1.5 dB at B = 1, and it reads as a real
    finding. `pedal_db` is raw. Same trap as `grunt_span_probe`'s (session 23); it
    cost this tool's first run.
    """
    d = json.load(open(REPORT))
    bands = d["meta"]["bands"]
    caps = {c["file"]: c for c in d["captures"]}
    cols = []
    for _, f in BLENDS:
        if f not in caps:
            sys.exit("report is missing %s" % f)
        if sweep not in caps[f]["fr"]:
            sys.exit("%s has no %s" % (f, sweep))
        fr = caps[f]["fr"][sweep]
        v = np.asarray(fr[key], dtype=float)
        if key == "plugin_db":
            v = v - float(fr["gain_db_applied"])
        cols.append(v)
    ref = cols[0]
    return bands, {b: [10.0 ** ((c[i] - ref[i]) / 20.0) for c in cols]
                   for i, b in enumerate(bands) if all(np.isfinite(c[i]) for c in cols)}


def fit_taper(t_by_band, bands, label, fixed=False):
    """Fit the 3 INTERIOR effective BLEND positions, shared across all bands.

    Legitimate as a nuisance, and bounded in what it can do: B is modelled as an
    exactly linear taper and a real pot is within ~10-20 %; the ENDPOINTS are immune
    (see the module docstring), so taper error can only move the three interior
    points and cannot absorb either b0 or a frequency-dependent defect. 3 shared
    parameters against 2 spare equations per band x N bands.

    ⚠ The MODEL is the control: the law is exact on it, so this fit MUST return
    0.250/0.500/0.750 there. If it ever does not, it is able to invent a taper and
    every pedal-side number below is worthless.
    """
    from scipy.optimize import least_squares

    def cost(p):
        out = []
        for b in bands:
            _, _, res, _ = quad_fit(t_by_band[b], p)
            t = t_by_band[b][1:]
            # scale-stable surrogate: residual on t^2 normalised by t, so a deep
            # null cannot dominate the fit through a dB blow-up
            B = np.asarray(list(p) + [1.0])
            A = np.vstack([B, B * B]).T
            k = np.linalg.lstsq(A, np.asarray(t) ** 2 - 1.0, rcond=None)[0]
            out.extend((1.0 + A @ k - np.asarray(t) ** 2) / np.maximum(np.asarray(t), 1e-4))
        return np.asarray(out)

    nominal = [0.25, 0.50, 0.75]
    if fixed:
        Bint = nominal
    else:
        sol = least_squares(cost, nominal, bounds=([0.02] * 3, [0.98] * 3),
                            xtol=1e-13, ftol=1e-13)
        Bint = list(sol.x)
    worst, nbad = 0.0, 0
    for b in bands:
        _, _, res, bad = quad_fit(t_by_band[b], Bint)
        nbad += bad
        if not bad:
            worst = max(worst, max(abs(x) for x in res))
    print("  %-6s interior B = %.4f / %.4f / %.4f  (nominal 0.25/0.50/0.75)   "
          "worst per-band |dt| = %.3f dB over %d bands%s"
          % (label, Bint[0], Bint[1], Bint[2], worst, len(bands),
             "" if nbad == 0 else "   (%d infeasible)" % nbad))
    return Bint, worst


def fold(rad):
    t = math.degrees(rad) % 360.0
    return 360.0 - t if t > 180.0 else t


def load_decompose():
    """{band: (|G|_model, theta_model_rad)} from a3_blend_decompose's exact taps.
    Its `od` column is a0.Vo through the shared post-BLEND chain and `ref` is Vc
    through the same chain, so od/ref IS this tool's G."""
    if not os.path.exists(DECOMPOSE_CSV):
        return None
    out = {}
    for line in open(DECOMPOSE_CSV):
        if line.startswith("#") or not line.strip():
            continue
        v = [float(x) for x in line.split(",")]
        ref, od, cl = complex(v[1], v[2]), complex(v[5], v[6]), complex(v[7], v[8])
        out[v[0]] = (abs(od) / abs(ref), cmath.phase(od) - cmath.phase(cl))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--validate", action="store_true")
    ap.add_argument("--fixed-taper", action="store_true",
                    help="assume an ideal linear BLEND taper (shows why it must be fitted)")
    args = ap.parse_args()

    b0 = model_b0()
    dec = load_decompose()
    print("bleed level taken from the model: b0 = %.5f (%+.2f dB). This axis is BLIND to it "
          "(degenerate) -- see the docstring." % (b0, 20 * math.log10(b0)))

    if args.selftest:
        if dec is None:
            sys.exit("selftest needs %s" % DECOMPOSE_CSV)
        print("\n=== SELFTEST: t(B) synthesised through the law from the decompose phasors ===")
        wr = wt = 0.0
        for f, (r, th) in sorted(dec.items()):
            g = r * cmath.exp(1j * th)
            t = [abs((1.0 - B * (1.0 - b0)) + B * g) for B, _ in BLENDS]
            k1, k2, _, _ = quad_fit(t, [0.25, 0.50, 0.75])
            rr, tt, _ = unpack(k1, k2, b0)
            wr = max(wr, abs(20 * math.log10(rr / r)))
            wt = max(wt, abs(fold(tt) - fold(th)))
        print("  worst |dr| = %.6f dB, worst |dtheta| = %.5f deg -> %s"
              % (wr, wt, "PASS" if wr < 1e-3 and wt < 1e-2 else "FAIL"))

    _, t_ped = load_totals("pedal_db", args.sweep)
    _, t_mdl = load_totals("plugin_db", args.sweep)
    bands = [b for b in sorted(t_ped) if b <= FIT_HI_HZ]

    print("\n=== 1. DOES THE PEDAL OBEY LevelBlend's MIXING LAW? (parameter-free in b0) ===")
    Bm, wm = fit_taper(t_mdl, bands, "MODEL", args.fixed_taper)
    Bp, wp = fit_taper(t_ped, bands, "PEDAL", args.fixed_taper)
    print("  take-to-take floor %.3f dB. MODEL must be ~0 (control); PEDAL below the floor"
          % TAKE_FLOOR_DB)
    print("  means the law HOLDS and the BLEND/LEVEL network is not A3's cause.")
    print("  VERDICT: law %s (pedal worst %.3f dB vs floor %.3f)"
          % ("HOLDS" if wp <= TAKE_FLOOR_DB else "FAILS", wp, TAKE_FLOOR_DB))

    if args.validate:
        if dec is None:
            sys.exit("validate needs %s" % DECOMPOSE_CSV)
        print("\n=== 2. VALIDATE: solve the MODEL's rendered totals vs its exact taps ===")
        print("     f   r_solved   r_taps    dr dB   th_solved  th_taps")
        drs = []
        for f in sorted(dec):
            b = min(t_mdl, key=lambda x: abs(x - f))
            if abs(b - f) > 0.06 * f:
                continue
            k1, k2, _, _ = quad_fit(t_mdl[b], Bm)
            r, th, _ = unpack(k1, k2, b0)
            rm, thm = dec[f]
            drs.append((f, 20.0 * math.log10(r / rm)))
            print("  %5.0f  %9.5f %9.5f  %+7.3f   %7.1f  %7.1f"
                  % (f, r, rm, drs[-1][1], fold(th), fold(thm)))
        sub = [d for f, d in drs if 40 <= f <= FIT_HI_HZ]
        print("  |dr| over 40-%.0f Hz: mean %.3f dB, worst %.3f dB"
              % (FIT_HI_HZ, np.mean(np.abs(sub)), np.max(np.abs(sub))))

    print("\n=== 3. A3 ON THE BLEND AXIS (%s, DRIVE/LEVEL noon, GRUNT cut, EQ flat) ==="
          % args.sweep)
    print("  r = |G| = the OD contribution at BLEND max, over the full-clean reference")
    print("  s_blend = the OD boost the model needs -- the quantity a3_shape_gate scores")
    print("     f   r_ped dB  r_mdl dB   s_blend dB   th_ped  th_mdl   |dt|p   cos_p")
    rows = []
    for b in sorted(t_ped):
        k1p, k2p, resp, badp = quad_fit(t_ped[b], Bp)
        k1m, k2m, _, _ = quad_fit(t_mdl[b], Bm)
        rp, thp, cp = unpack(k1p, k2p, b0)
        rm, thm, _ = unpack(k1m, k2m, b0)
        dt = float("nan") if badp else max(abs(x) for x in resp)
        ok = (not badp) and dt <= 0.30 and abs(cp) <= 1.02 and rp > 1e-20
        s = 20.0 * math.log10(rp / rm) if rp > 1e-20 else float("nan")
        rows.append((b, s, ok))
        print("  %5.0f  %+8.2f  %+8.2f    %+8.2f    %6.1f  %6.1f   %5.3f  %+7.2f%s"
              % (b, 20 * math.log10(rp), 20 * math.log10(rm), s, fold(thp), fold(thm),
                 dt, cp, "" if ok else "   <- NOT identified"))

    trust = [x for x in rows if x[2] and x[0] <= FIT_HI_HZ]
    print("\n  identified bands below %.0f Hz: %d of %d"
          % (FIT_HI_HZ, len(trust), len([x for x in rows if x[0] <= FIT_HI_HZ])))
    if trust:
        v = [x[1] for x in trust]
        print("  s_blend there: mean %+.2f dB, min %+.2f, max %+.2f, rms %.2f dB"
              % (np.mean(v), min(v), max(v), float(np.sqrt(np.mean(np.square(v))))))

    # ---- cross-check against the DRIVE axis, the only other estimate of the same thing ----
    print("\n=== 4. CROSS-CHECK vs the DRIVE axis (a3_phase_solve / a3_shape_gate) ===")
    print("  Both estimate the SAME quantity from disjoint information: the drive axis breaks")
    print("  the (r, theta) trade with mu_d's shape across five DRIVE captures, this axis with")
    print("  the B-dependence of one. A disagreement means at least one is being misread.")
    try:
        import a3_phase_solve as ps
        mdl_d = ps.load_model([0.0, 0.25, 0.5, 0.75, 1.0])
        ped_d = ps.load_pedal(args.sweep)
        beta_db = 20.0 * math.log10(b0)
        print("      f   s_drive dB   s_blend dB    diff    th_drive  th_blend")
        diffs = []
        for f in ps.PROBE_BANDS:
            if f not in mdl_d[0.5]:
                continue
            mu = [mdl_d[d][f][0] for d in [0.0, 0.25, 0.5, 0.75, 1.0]]
            (th_d, _, s_d), _ = ps.fit_band(ped_d[f], mu, beta_db)
            b = min(t_ped, key=lambda x: abs(x - f))
            row = next((r for r in rows if r[0] == b), None)
            if row is None or not row[2]:
                continue
            k1p, k2p, _, _ = quad_fit(t_ped[b], Bp)
            _, thp, _ = unpack(k1p, k2p, b0)
            sd = 20.0 * math.log10(s_d)
            diffs.append(sd - row[1])
            print("  %5.0f    %+8.2f    %+8.2f   %+7.2f     %6.1f    %6.1f"
                  % (f, sd, row[1], diffs[-1], math.degrees(th_d), fold(thp)))
        if diffs:
            print("  drive-minus-blend: mean %+.2f dB, worst %+.2f dB, rms %.2f dB"
                  % (np.mean(diffs), max(diffs, key=abs), float(np.sqrt(np.mean(np.square(diffs))))))
    except Exception as exc:                                       # noqa: BLE001
        print("  (skipped: %s)" % exc)

    # ---- emit the pedal's measured OD transfer as a fit target ----
    out = "build/a3_blend_axis_%s.csv" % args.sweep
    with open(out, "w") as fh:
        fh.write("# a3_blend_axis %s: the PEDAL's OD-path transfer measured on the BLEND axis.\n"
                 "# r = |G| = OD contribution at BLEND max over the full-clean reference;\n"
                 "# theta identified only up to sign. b0 = %.5f (fixed -- this axis is blind to it).\n"
                 "# interior BLEND taper fitted at %.4f/%.4f/%.4f.\n"
                 "# f,r_ped,theta_ped_deg,r_mdl,theta_mdl_deg,identified\n"
                 % (args.sweep, b0, Bp[0], Bp[1], Bp[2]))
        for b in sorted(t_ped):
            k1p, k2p, _, _ = quad_fit(t_ped[b], Bp)
            k1m, k2m, _, _ = quad_fit(t_mdl[b], Bm)
            rp, thp, _ = unpack(k1p, k2p, b0)
            rm, thm, _ = unpack(k1m, k2m, b0)
            ok = next((r[2] for r in rows if r[0] == b), False)
            fh.write("%.0f,%.6e,%.3f,%.6e,%.3f,%d\n"
                     % (b, rp, fold(thp), rm, fold(thm), int(ok)))
    print("\n  wrote %s (the pedal's measured OD-path transfer -- the A3 fit target)" % out)


if __name__ == "__main__":
    main()
