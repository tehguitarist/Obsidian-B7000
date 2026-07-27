#!/usr/bin/env python3.11
"""a3_phase_solve — session 31 (Phase 9 / A3 step 1): SOLVE for the pedal's own
OD-vs-bleed PHASE per band, instead of estimating it.

Session 29 established that the pedal's OD path partially cancels the clean BLEND
bleed below ~80 Hz and quantified the requirement as "~140-180 deg at 40 Hz
decaying to ~0 by 200 Hz". That was an inference from one drive setting, where the
geometry is genuinely under-determined: a single |1 + m e^(i0)| = T equation has
two unknowns (m, 0), which is exactly why a3_solve.py could only report "the phase
required IF the OD magnitude were left at the model's value".

The DRIVE SWEEP removes that ambiguity. Five captures (drive min / 9:30 / noon /
2:30 / max) share one signal path and differ only in how hard the OD path is
driven, so per band they give FIVE equations:

    t_d = beta * |1 + s * mu_d * e^(i.theta)|        d = 1..5

  t_d    pedal total at drive d, relative to its own full-clean capture (measured)
  mu_d   the MODEL's |od|/|bleed| ratio at that drive and band (a3_blend_decompose)
  s      one per-band scale on the OD magnitude          (unknown)
  theta  the pedal's OD-vs-bleed phase at that band      (unknown)
  beta   the pedal's clean-bleed level, ONE GLOBAL real  (unknown)

Two unknowns per band against five equations => overdetermined, and beta is shared
across every band, so it is measured here rather than assumed. beta is legitimately
frequency-flat: the bleed path is clean -> BLEND -> post-BLEND and the full-clean
reference is clean -> BLEND(=0) -> post-BLEND, so the shared post-BLEND chain
cancels exactly and what is left is a resistive divider ratio (LevelBlend has no
caps at all). That is the same flatness the pedal's own drive-min curve shows.

WHAT IS ASSUMED, AND HOW IT IS CHECKED:
  * theta does not depend on the drive knob. MEASURED true in the model
    (od_phase_probe across drive 0..1 moves the OD phase by <0.1 deg at every
    band), and the per-band residual below tests it on the pedal -- with 5
    equations and 2 unknowns a drive-dependent phase cannot hide.
  * the model gets the SHAPE of the drive-dependence right at each band (only the
    per-band level s is free). Weaker than assuming mu_d is frequency-independent;
    again the residual is the test.
  * a wide confidence interval is reported per band (all theta within +0.5 dB RMS
    of the optimum), because a phase solved from magnitudes alone is only as
    sharp as the cancellation is deep. Read the interval, not just the point.

Self-test (--selftest): re-solve against data SYNTHESISED from the model itself.
It must return theta = the model's own phase and s = 1.000, or the solver is wrong.

Usage:
    python3.11 analysis/a3_phase_solve.py [--sweep sweep_drv_-18] [--selftest]
Needs build/a3_dec_drv{0.0,0.25,0.5,0.75,1.0}.csv from:
    for d in 0.0 0.25 0.5 0.75 1.0; do
      ./build/a3_blend_decompose 1 $d -18 > build/a3_dec_drv$d.csv; done
(the dBFS argument must match the report sweep being read).
"""
import argparse
import cmath
import json
import math
import os
import sys

import numpy as np

REPORT = "analysis/reports/comprehensive_data.json"

# (drive knob value, capture file). ref-od IS drive noon (captures.py::_REF_OD).
DRIVES = [
    (0.00, "drive-0700_base-od.wav"),
    (0.25, "drive-0930_base-od.wav"),
    (0.50, "ref-od.wav"),
    (0.75, "drive-1430_base-od.wav"),
    (1.00, "drive-1700_base-od.wav"),
]
CLEAN_REF = "blend-0700_base-od.wav"          # BLEND fully counter-clockwise = full clean

# The decompose probe's bands; matched to the report's 1/3-oct centres by nearest.
PROBE_BANDS = [20, 25, 32, 40, 50, 64, 80, 101, 127, 160, 202, 254,
               320, 403, 508, 640, 806]


def load_model(drive_vals, prefix="build/a3_dec_drv"):
    """{drive: {band: (mu, theta_model_rad, bleed_db_rel_ref)}} from a3_blend_decompose."""
    out = {}
    for d in drive_vals:
        path = "%s%s.csv" % (prefix, d)
        if not os.path.exists(path):
            sys.exit("missing %s -- see this file's docstring for the command" % path)
        rows = {}
        for line in open(path):
            if line.startswith("#") or not line.strip():
                continue
            v = [float(t) for t in line.strip().split(",")]
            f, ref = v[0], complex(v[1], v[2])
            od, cl = complex(v[5], v[6]), complex(v[7], v[8])
            rows[int(f)] = (
                abs(od) / abs(cl),
                (cmath.phase(od) - cmath.phase(cl)),
                20.0 * math.log10(abs(cl) / abs(ref)),
            )
        out[d] = rows
    return out


def load_pedal(sweep):
    """{band: [t_d in dB relative to the pedal's own full-clean capture]}."""
    d = json.load(open(REPORT))
    bands = d["meta"]["bands"]
    caps = {c["file"]: c for c in d["captures"]}
    for f in [CLEAN_REF] + [c for _, c in DRIVES]:
        if f not in caps:
            sys.exit("report is missing %s" % f)

    def ped(fname):
        fr = caps[fname]["fr"]
        if sweep not in fr:
            sys.exit("%s has no %s" % (fname, sweep))
        return fr[sweep]["pedal_db"]          # RAW pedal transfer, no gain-match applied

    ref = ped(CLEAN_REF)
    cols = [ped(c) for _, c in DRIVES]
    out = {}
    for b in PROBE_BANDS:
        i = min(range(len(bands)), key=lambda k: abs(bands[k] - b))
        out[b] = [c[i] - ref[i] for c in cols]
    return out


def identifiable_theta(deg):
    """Fold a phase onto the range the magnitudes can actually identify: [0, 180].

    `model[d][b][1]` is a DIFFERENCE of two cmath.phase values, so it lives in
    (-360, 360] and is NOT a principal value -- at 20 Hz it reads +183.02 deg.
    Magnitudes identify theta only modulo 360 AND up to sign (conjugating theta
    leaves every |.| unchanged), which is why fit_band searches [0, pi]. So the
    reference the self-test compares against has to be folded the same way, or a
    true value that crosses anti-phase is scored against a solver that cannot
    represent it: 183.02 was compared to the correct answer 177.00 and called a
    6.0 deg failure.

    ⚠ This is a test-reference bug, NOT a licence to loosen the gate -- after the
    fold the same band agrees to 0.02 deg. It stayed hidden until trebleC7 moved
    the model's LF phase past 180 deg, which is exactly when it started to matter.
    """
    t = float(deg) % 360.0
    return 360.0 - t if t > 180.0 else t


def model_db(beta_db, s, mu, theta):
    """20log10( beta * |1 + s*mu*e^(i.theta)| ) per drive."""
    return [beta_db + 20.0 * math.log10(max(abs(1.0 + s * m * cmath.exp(1j * theta)), 1e-12))
            for m in mu]


def fit_band(t_db, mu, beta_db, n_theta=1441, n_s=2401):
    """Least squares over (theta, s) at fixed beta, by grid on BOTH.

    ⚠ Do NOT replace the s search with a golden section: at fixed theta with
    cos(theta) < 0 the predicted level |1 + s.mu.e^(i.theta)| DIPS through the
    cancellation and rises again, so the cost is bimodal in s and a unimodal
    search silently converges to the wrong branch. The self-test caught exactly
    that (band 20 came back 7 deg off with an rms of 0.27 dB on data synthesised
    from the model itself, i.e. where the residual must be 0).
    """
    mu = np.asarray(mu, dtype=float)
    t = np.asarray(t_db, dtype=float)
    # theta in [0, pi]: the SIGN is unobservable from magnitudes alone
    # (conjugating theta leaves every |.| unchanged), so only |theta| is identifiable.
    thetas = np.linspace(0.0, math.pi, n_theta)
    s = 10.0 ** np.linspace(-4.0, 4.0, n_s)
    prof = np.empty(n_theta)
    s_at = np.empty(n_theta)
    for j, th in enumerate(thetas):
        z = s[:, None] * mu[None, :] * cmath.exp(1j * th)      # (n_s, n_drive)
        pred = beta_db + 20.0 * np.log10(np.maximum(np.abs(1.0 + z), 1e-12))
        cost = np.mean((pred - t[None, :]) ** 2, axis=1)
        k = int(np.argmin(cost))
        prof[j], s_at[j] = cost[k], s[k]
    j = int(np.argmin(prof))

    # LOCAL POLISH around the global winner. The coarse grid is what protects
    # against the bimodality in s (above), but its quantisation is not harmless:
    # near anti-phase |1 + s.mu.e^(i.theta)| is extremely sensitive to theta, so
    # the 0.125 deg step left a 0.012 dB residual at 32 Hz on data synthesised
    # from the model itself, where it must be 0 (session 47). Refine on a fine
    # grid spanning +-2 coarse steps in BOTH axes -- global search first, local
    # refinement second, so no branch can be jumped.
    dth = thetas[1] - thetas[0]
    th_f = np.linspace(max(0.0, thetas[j] - 2 * dth), min(math.pi, thetas[j] + 2 * dth), 81)
    r = (s[1] / s[0]) ** 2
    s_f = np.geomspace(s_at[j] / r, s_at[j] * r, 81)
    zf = s_f[:, None, None] * mu[None, None, :] * np.exp(1j * th_f[None, :, None])
    pf = beta_db + 20.0 * np.log10(np.maximum(np.abs(1.0 + zf), 1e-12))
    cf = np.mean((pf - t[None, None, :]) ** 2, axis=2)
    ki, kj = np.unravel_index(int(np.argmin(cf)), cf.shape)
    if cf[ki, kj] < prof[j]:
        return (th_f[kj], cf[ki, kj], s_f[ki]), (thetas, prof)
    return (thetas[j], prof[j], s_at[j]), (thetas, prof)


def interval(prof, jbest, slack_db=0.5):
    """All theta whose best-fit RMS is within slack_db of the optimum."""
    thetas, cost = prof
    lim = (math.sqrt(jbest) + slack_db) ** 2
    ok = thetas[cost <= lim]
    return (math.degrees(ok.min()), math.degrees(ok.max())) if ok.size else (float("nan"),) * 2


def solve(pedal, model, beta_db):
    res = {}
    for b in PROBE_BANDS:
        mu = [model[d][b][0] for d, _ in DRIVES]
        best, prof = fit_band(pedal[b], mu, beta_db)
        res[b] = dict(theta=math.degrees(best[0]), rms=math.sqrt(best[1]), s=best[2],
                      lo=interval(prof, best[1])[0], hi=interval(prof, best[1])[1])
    return res


def fit_beta(pedal, model):
    """One global bleed level. Scan; the per-band fit is re-run at each candidate."""
    best = None
    for k in range(-260, -100):
        beta_db = k / 10.0
        tot = 0.0
        for b in PROBE_BANDS:
            mu = [model[d][b][0] for d, _ in DRIVES]
            (_, j, _), _ = fit_band(pedal[b], mu, beta_db, n_theta=181, n_s=1201)
            tot += j
        if best is None or tot < best[1]:
            best = (beta_db, tot)
    return best[0]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--beta-db", type=float, default=None,
                    help="pedal bleed level rel. its full-clean capture; default = fitted")
    ap.add_argument("--csv-prefix", default="build/a3_dec_drv",
                    help="a3_blend_decompose CSV prefix (swap in a candidate render)")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    model = load_model([d for d, _ in DRIVES], args.csv_prefix)
    bleed_model = model[0.50][40][2]

    if args.selftest:
        # Synthesise the pedal from the model itself: same bleed, s = 1, theta =
        # the model's own phase. The solver must recover both.
        pedal = {b: model_db(bleed_model, 1.0,
                             [model[d][b][0] for d, _ in DRIVES], model[0.50][b][1])
                 for b in PROBE_BANDS}
        res = solve(pedal, model, bleed_model)
        print("SELF-TEST: solve against data synthesised from the model itself.")
        print("%6s %10s %10s %8s %8s" % ("f", "theta_true", "theta_fit", "s_fit", "rms"))
        worst_t = worst_s = 0.0
        for b in PROBE_BANDS:
            true = identifiable_theta(math.degrees(model[0.50][b][1]))
            r = res[b]
            worst_t = max(worst_t, abs(r["theta"] - true))
            worst_s = max(worst_s, abs(r["s"] - 1.0))
            print("%6d %10.2f %10.2f %8.4f %8.4f  [%6.1f,%6.1f] %s"
                  % (b, true, r["theta"], r["s"], r["rms"], r["lo"], r["hi"],
                     "in" if r["lo"] - 1e-6 <= true <= r["hi"] + 1e-6 else "OUT"))
        print("\nworst |dtheta| = %.3f deg, worst |s-1| = %.5f" % (worst_t, worst_s))

        # ⚠ A FLAT DEGREE THRESHOLD IS THE WRONG GATE for a quantity that is only
        # INTERVAL-identified, and it went red for exactly that reason (session 47).
        # At 806 Hz mu is small, so |1 + s.mu.e^(i.theta)| ~ 1 + s.mu.cos(theta) and
        # only the PRODUCT s.mu.cos(theta) is determined: theta anywhere in [0, 59]
        # reproduces the synthesised data to within 0.01 dB rms. The solver returned
        # 45.75 against a true 46.30 -- 0.55 deg "wrong" at a residual of 8.9e-08,
        # against a true-point residual of exactly 0. That is the DATA being flat,
        # not the solver being wrong, and loosening the 0.5 deg number would hide the
        # real finding (theta is unidentified above ~500 Hz) instead of stating it.
        #
        # So the gate is now what "trustworthy" actually means here:
        #   (a) the fit REPRODUCES the synthesised data (residual ~ 0) -- if the
        #       solver were broken this is what would break;
        #   (b) the true theta lies INSIDE the band's own reported interval -- the
        #       interval is the tool's own claim, so this tests the claim it makes;
        #   (c) the point estimate is held to 0.5 deg ONLY where the interval is
        #       narrow enough for a point estimate to mean anything.
        # Report (c)'s scope explicitly so a widening interval can never quietly
        # shrink the gate.
        NARROW_DEG = 20.0
        bad_rms, bad_in, bad_pt, narrow = [], [], [], []
        for b in PROBE_BANDS:
            true = identifiable_theta(math.degrees(model[0.50][b][1]))
            r = res[b]
            if r["rms"] > 0.01:
                bad_rms.append(b)
            if not (r["lo"] - 1e-6 <= true <= r["hi"] + 1e-6):
                bad_in.append(b)
            if (r["hi"] - r["lo"]) <= NARROW_DEG:
                narrow.append(b)
                if abs(r["theta"] - true) >= 0.5:
                    bad_pt.append(b)
        print("residual <= 0.01 dB at every band: %s" % ("YES" if not bad_rms else "NO %s" % bad_rms))
        print("true theta inside its own interval:  %s" % ("YES" if not bad_in else "NO %s" % bad_in))
        print("point estimate < 0.5 deg on the %d NARROW bands (interval <= %.0f deg) %s: %s"
              % (len(narrow), NARROW_DEG, narrow, "YES" if not bad_pt else "NO %s" % bad_pt))
        ok = not (bad_rms or bad_in or bad_pt) and worst_s < 0.05
        print("PASS" if ok else "FAIL -- solver is not trustworthy")
        return

    pedal = load_pedal(args.sweep)

    # ---- 1. the raw evidence ------------------------------------------------
    print("A3 phase solve -- the pedal's OD-vs-bleed phase, from the DRIVE SWEEP.")
    print("sweep = %s, model = a3_blend_decompose (grunt cut, BLEND max).\n" % args.sweep)
    print("1. PEDAL total per drive, dB relative to its own full-clean capture,")
    print("   alongside the MODEL's |od|/|bleed| ratio mu_d at the same settings.\n")
    print("%6s %s   | %s" % ("f", "".join("%8s" % ("drv%.2f" % d) for d, _ in DRIVES),
                             "".join("%7s" % ("mu%.2f" % d) for d, _ in DRIVES)))
    for b in PROBE_BANDS:
        print("%6d %s   | %s"
              % (b, "".join("%8.1f" % v for v in pedal[b]),
                 "".join("%7.2f" % model[d][b][0] for d, _ in DRIVES)))
    print("\n   ⚠ The model's mu_d is NON-MONOTONE in drive (it peaks at 2:30 and FALLS")
    print("   by max) while the pedal's must keep growing straight through the null and")
    print("   out the far side. That is a separate, real drive-axis error and it is why")
    print("   the least-squares in part 3 cannot fit 40-101 Hz well.")

    # ---- 2. the assumption-free bound ---------------------------------------
    print("\n\n2. ASSUMPTION-FREE LOWER BOUND on the pedal's phase, from the null DEPTH.")
    print("   As the OD magnitude m sweeps over the positive reals, |1 + m.e^(i.theta)|")
    print("   traces a ray from 1 and its closest approach to the origin is |sin theta|.")
    print("   So the DEEPEST total measured at any drive, T = min_d t_d / beta, gives")
    print("        |sin theta| <= T   =>   theta >= 180 - asin(T)")
    print("   using ONE capture per band and NO model of how the OD grows with drive.")
    print("   Blank = the pedal never dips below its bleed there, so nothing is forced.\n")
    print("   1/3-octave banding can only FILL a null, never deepen it, so the measured")
    print("   depth understates the true one and this bound is conservative.\n")
    betas = sorted({round(b, 2) for b in
                    (args.beta_db, -15.2, bleed_model, -18.0) if b is not None})
    print("%6s %s   %10s %9s" % ("f", "".join("%10s" % ("beta=%.1f" % x) for x in betas),
                                 "theta_mdl", "deficit"))
    bound = {}
    for b in PROBE_BANDS:
        cells, first = [], None
        for x in betas:
            T = 10.0 ** ((min(pedal[b]) - x) / 20.0)
            if T <= 1.0:
                th = 180.0 - math.degrees(math.asin(T))
                cells.append("%10.1f" % th)
                first = th if first is None else min(first, th)
            else:
                cells.append("%10s" % "-")
        mdl = math.degrees(model[0.50][b][1])
        bound[b] = first
        print("%6d %s   %10.1f %9s"
              % (b, "".join(cells), mdl, "-" if first is None else ">= %.0f" % (first - mdl)))
    print("\n   'deficit' uses the WEAKEST beta in the row, so it too is a lower bound.")
    print("   ⚠ theta_mdl is SIGNED and goes NEGATIVE above ~90 Hz. Sessions 31/32 printed")
    print("   |theta_mdl| here and differenced that, which understates the extra phase the")
    print("   model needs by 2|theta_mdl| — 15 deg at 101 Hz rising to 76 deg at 202-254.")

    # ---- 3. the least-squares (secondary) -----------------------------------
    beta_db = args.beta_db if args.beta_db is not None else fit_beta(pedal, model)
    res = solve(pedal, model, beta_db)
    print("\n\n3. LEAST-SQUARES over all 5 drive points (secondary -- it inherits the")
    print("   model's mu_d shape, which part 1 shows is wrong on the drive axis).\n")
    print("Pedal bleed  beta = %+.2f dB (fitted, one global constant); model bleed %+.2f dB"
          % (beta_db, bleed_model))
    print("=> the model's bleed sits %.2f dB %s than the pedal's.\n"
          % (abs(bleed_model - beta_db), "LOWER" if bleed_model < beta_db else "HIGHER"))
    print("theta = |OD-vs-bleed phase|; its SIGN is not identifiable from magnitudes.")
    print("[lo,hi] = every theta fitting within +0.5 dB RMS of the optimum.")
    print("theta_mdl is SIGNED (it crosses zero near 90 Hz); 'extra' = theta_ped - theta_mdl")
    print("is the phase an added OD-path element must supply, on the branch where the")
    print("pedal's theta stays POSITIVE — see the branch discussion in a3_lead_design.py.\n")
    print("%6s %9s %14s %8s %8s %10s %9s"
          % ("f", "theta_ped", "[lo, hi]", "rms_dB", "s", "theta_mdl", "extra"))
    for b in PROBE_BANDS:
        r = res[b]
        mdl = math.degrees(model[0.50][b][1])
        print("%6d %9.1f  [%5.1f,%6.1f] %8.2f %8.2f %10.1f %9.1f"
              % (b, r["theta"], r["lo"], r["hi"], r["rms"], r["s"], mdl, r["theta"] - mdl))

    bad = [b for b in PROBE_BANDS if res[b]["rms"] > 2.0]
    if bad:
        print("\nNOTE: rms > 2 dB at %s Hz -- the 5-point drive shape does not fit there"
              % ", ".join(str(b) for b in bad))
        print("under a drive-independent phase, so treat those bands' theta as weak.")


if __name__ == "__main__":
    main()
