#!/usr/bin/env python3.11
"""a3_lead_fit -- Phase 9 / A3 step 3b (session 35): fit the residual OD-path
element AND the bleed level beta JOINTLY, scored against the RAW captures.

WHY THIS IS NOT a3_lead_design
------------------------------
`a3_lead_design` fits a network to a DERIVED target: per band it first solves
(s, theta) from the drive sweep, then asks a network to reproduce that (s, theta).
That is one inference too many. The per-band solve is only as sharp as the
cancellation is deep, so it hands back wide intervals (at 127 Hz theta is
[29, 99] deg) and then the network is fitted to the POINT ESTIMATE as if it were
a measurement. A candidate that misses the point estimate by 40 deg but sits
comfortably inside the interval is scored as a failure, and one that hits the
point estimate at a band where the interval is 70 deg wide is scored as a success.

This tool removes the intermediate entirely. A candidate is a transfer function
H(f) and a bleed level beta; together they predict the pedal's measured total at
every (band, drive) directly:

    pred_dB(b, d) = beta + 20 log10 | 1 + |H(b)| . mu_d(b) . e^(i(theta_mdl(b,d) + arg H(b))) |

and the score is the residual against the five measured drive totals. No target,
no transcription, no point estimate. beta is just another free parameter, which
is what "fit beta jointly, never before or after" (session 33 item 3) actually
requires -- the phase target is a FUNCTION of beta, so any procedure that fixes
one first has no fixed point.

WHAT IT REPORTS
---------------
  * the NO-ELEMENT baseline (H = 1, beta free) -- how much work is actually left
    for an element to do after trebleC7. If this is already small, the honest
    answer is "do not build one".
  * each candidate family's best joint (H, beta), with the per-band residual.
  * the residual an ORACLE element achieves: per band, the best (s, theta) with
    NO causality constraint linking them. That is the floor any causal network
    must sit above, so (family residual - oracle residual) separates "this family
    is too simple" from "no causal element can do this".

Self-test: synthesise the pedal from the model through a KNOWN network at a KNOWN
beta and confirm both are recovered.

Usage:
    python3.11 analysis/a3_lead_fit.py [--sweep sweep_drv_-18] [--selftest]
Needs build/a3_dec_drv{0.0,0.25,0.5,0.75,1.0}.csv (see a3_phase_solve's docstring).
"""
import argparse
import math
import os
import sys

import numpy as np
from scipy.optimize import minimize

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_phase_solve as ps                                      # noqa: E402
import a3_lead_design as ld                                      # noqa: E402

# Same band policy as a3_lead_design: 320 Hz is the TrebleAttack-notch band (a
# known separate gap, GAP #2) and is excluded outright; above 254 Hz mu < 1 so the
# total is bleed-dominated and the band constrains the tail, not the fit.
CORE_HI = 254
EXCLUDE = {320}
WEAK_W = 0.15

# Spec kind "o" = a zero pinned at the ORIGIN, i.e. a true first-order high-pass
# rather than a shelf. This is the physically important comparison: a coupling cap
# working into a resistance gives an origin zero, whereas a lead/shelf needs a
# resistor bridging the cap as well. The free-zero fits put the zero at 0.3-6.5 Hz
# depending on stimulus level -- i.e. BELOW the 20 Hz measurement floor and not
# identified -- so "is it just one more coupling corner?" has to be asked directly.

# ⚠ The 4th field is fix_k: TRUE pins the broadband gain at exactly 1, so the row
# really is "the model as it stands, no element at all". It is not decoration.
# Until session 37 the first row was LABELLED "none (H = 1)" but still fitted a
# free scalar k along with beta -- at the shipped state it came back k = 1.898,
# i.e. the "no element" baseline every previous session quoted was secretly the
# model plus +5.6 dB of broadband OD gain. That makes the baseline HARDER to beat
# (so the elements' improvements were understated, not overstated), but it also
# means the null-gate row under that label was NOT the shipped model's null, and
# it hid a real finding: at the shipped state the fit wants the OD path several dB
# hotter. Both rows are now printed so the two questions stay separate.
FAMILIES = [
    ("none: the model as it stands (H = 1)", [], [], True),
    ("broadband OD gain only (H = k)", [], [], False),
    ("1st-order HIGH-PASS (coupling cap)", ["o"], ["r"], False),
    ("2nd-order high-pass", ["o", "o"], ["r", "r"], False),
    ("1 zero / 1 pole  (lead/shelf)", ["r"], ["r"], False),
    ("2 real zeros / 2 real poles (lag-lead)", ["r", "r"], ["r", "r"], False),
    ("complex pair / complex pair", ["c"], ["c"], False),
    ("3 zeros / 3 poles", ["c", "r"], ["c", "r"], False),
]


# --- local section/unpack, extending a3_lead_design's with the origin zero -----
# Kept here rather than edited into a3_lead_design so that tool's published
# numbers stay reproducible; everything else is imported from it.
def _sec(s, spec):
    if spec[0] == "o":                     # zero at the origin: a true high-pass
        return s
    return ld._sec(s, spec)


def response(f, k, zeros, poles):
    s = 2j * math.pi * np.asarray(f, dtype=float)
    h = np.full(s.shape, complex(k))
    for z in zeros:
        h = h * _sec(s, z)
    for p in poles:
        h = h / _sec(s, p)
    return h


def _unpack(v, kinds):
    """As a3_lead_design._unpack, but kind 'o' consumes NO parameter."""
    out, i = [], 0
    for kind in kinds:
        if kind == "o":
            out.append(("o",))
            continue
        f = math.exp(min(max(v[i], math.log(0.1)), math.log(1e5))); i += 1
        if kind == "r":
            out.append(("r", f))
        else:
            q = math.exp(min(max(v[i], math.log(0.05)), math.log(20.0))); i += 1
            out.append(("c", f, q))
    return out, i


def describe(zeros, poles, k):
    def one(spec):
        if spec[0] == "o":
            return "s (origin)"
        return "f=%.1f" % spec[1] if spec[0] == "r" else "f=%.1f Q=%.2f" % (spec[1], spec[2])
    return ("k=%.3g | zeros: %s | poles: %s"
            % (k, "; ".join(one(z) for z in zeros) or "-",
               "; ".join(one(p) for p in poles) or "-"))


def measured(pedal, bands):
    """(nband, ndrive) array of the pedal's totals rel. its own full-clean capture."""
    return np.array([pedal[b] for b in bands], dtype=float)


def model_arrays(model, bands):
    """mu (nband, ndrive) and theta_mdl (nband, ndrive) in radians."""
    drives = [d for d, _ in ps.DRIVES]
    mu = np.array([[model[d][b][0] for d in drives] for b in bands])
    th = np.array([[model[d][b][1] for d in drives] for b in bands])
    return mu, th


def predict(beta_db, hmag, hph, mu, th):
    """beta + 20log10|1 + |H| mu e^(i(theta_mdl + arg H))| for every (band, drive)."""
    z = (hmag[:, None] * mu) * np.exp(1j * (th + hph[:, None]))
    return beta_db + 20.0 * np.log10(np.maximum(np.abs(1.0 + z), 1e-12))


def resid_rms(beta_db, hmag, hph, mu, th, meas, w):
    e = predict(beta_db, hmag, hph, mu, th) - meas
    return float(np.sqrt(np.sum(w[:, None] * e * e) / (np.sum(w) * e.shape[1])))


def fit_family(bands, kinds_z, kinds_p, mu, th, meas, w, ntry=40, seed=11, fix_k=False):
    """Joint fit of (network, beta). beta is a free parameter, not a pre-set.

    fix_k pins the broadband gain at exactly 1 so a row can mean "no element at
    all" rather than "no shaping but any level" -- see the FAMILIES comment.
    """
    rng = np.random.default_rng(seed)
    F = np.asarray(bands, dtype=float)
    npar = len(kinds_z) + len(kinds_p)

    def unpack(v):
        zn, i = _unpack(v, kinds_z)
        pn, j = _unpack(v[i:], kinds_p)
        if fix_k:
            return zn, pn, 0.0, v[i + j]               # log-gain pinned at 0 => k = 1
        return zn, pn, v[i + j], v[i + j + 1]          # + log-gain, beta

    def cost(v):
        zn, pn, lk, beta = unpack(v)
        if not (-40.0 < beta < 0.0) or abs(lk) > 10.0:
            return 1e9
        try:
            h = response(F, math.exp(lk), zn, pn)
        except (FloatingPointError, OverflowError):
            return 1e9
        a = np.abs(h)
        if not np.all(np.isfinite(a)) or np.any(a <= 0):
            return 1e9
        return resid_rms(beta, a, np.angle(h), mu, th, meas, w)

    best = (float("inf"), None)
    for _ in range(ntry):
        v0 = []
        for kind in list(kinds_z) + list(kinds_p):
            if kind == "o":                        # origin zero carries no parameter
                continue
            v0.append(math.log(10 ** rng.uniform(1.0, 3.0)))
            if kind == "c":
                v0.append(math.log(10 ** rng.uniform(-0.4, 0.5)))
        if not fix_k:
            v0.append(rng.uniform(-0.5, 0.5))
        v0.append(rng.uniform(-19.0, -15.0))
        r = minimize(cost, np.array(v0), method="Nelder-Mead",
                     options=dict(maxiter=40000, maxfev=40000, xatol=1e-7, fatol=1e-10))
        if r.fun < best[0]:
            best = (r.fun, r.x)
    zn, pn, lk, beta = unpack(best[1])
    return dict(rms=best[0], z=zn, p=pn, k=math.exp(lk), beta=beta, npar=npar + 2)


def oracle(bands, mu, th, meas, beta_db):
    """Per band, the best (s, dphi) with NO causality link between them.

    This is the floor: it is what an element could do if its magnitude and phase
    were independently choosable at every frequency, which no real network allows.
    A family sitting ON this floor is limited by the DATA; one far above it is
    limited by its own order.
    """
    out = []
    for i, b in enumerate(bands):
        gs = 10.0 ** np.linspace(-1.5, 1.5, 601)
        gp = np.radians(np.linspace(-180.0, 180.0, 721))
        z = gs[:, None, None] * mu[i][None, None, :] * np.exp(1j * (th[i][None, None, :] + gp[None, :, None]))
        pred = beta_db + 20.0 * np.log10(np.maximum(np.abs(1.0 + z), 1e-12))
        c = np.mean((pred - meas[i][None, None, :]) ** 2, axis=2)
        j = np.unravel_index(int(np.argmin(c)), c.shape)
        out.append((gs[j[0]], math.degrees(gp[j[1]]), math.sqrt(c[j])))
    return out


def clean_side_test(bands, mu, th, meas, w, beta0):
    """Test whether the residual could be on the CLEAN/bleed side instead of the
    OD side. A frequency-dependent correction on the clean/bleed term is
    mathematically a per-band, drive-INDEPENDENT dB offset (it multiplies the
    whole (1 + mu.e^{i theta}) bracket, so its magnitude effect is the same at
    every drive for a given band -- see docs/phase9-validation.md for the algebra).
    Physically this must be so anyway: the clean bleed provably does not depend
    on DRIVE (DRIVE only touches the OD gain stage, downstream of where the clean
    tap splits off at IC1_A), which a3_phase_solve's docstring already asserts and
    session 34 verified directly on the model (clean column identical to 0.00e0 dB
    across all five drives).

    So this fits ONE constant per band (no shared shape across bands, maximally
    generous to the clean-side hypothesis) and reports whether that closes the
    gap the OD-side element closes. If the per-band beta cannot reproduce the
    drive-dependent part of the residual, the defect cannot be on the clean side
    at any frequency shape, because no clean-side shelf can vary by drive.
    """
    out = []
    for i, b in enumerate(bands):
        pred0 = predict(0.0, np.ones(1), np.zeros(1), mu[i:i + 1], th[i:i + 1])[0]
        # best constant dB offset for this band, least squares over its 5 drives
        off = float(np.mean(meas[i] - pred0))
        resid = float(np.sqrt(np.mean((pred0 + off - meas[i]) ** 2)))
        out.append(resid)
    return np.array(out)


def per_band(beta_db, hmag, hph, mu, th, meas):
    e = predict(beta_db, hmag, hph, mu, th) - meas
    return np.sqrt(np.mean(e * e, axis=1))


def selftest():
    print("SELF-TEST: recover a KNOWN network and a KNOWN beta from synthesised data.\n")
    model = ps.load_model([d for d, _ in ps.DRIVES])
    bands = [b for b in ps.PROBE_BANDS if b not in EXCLUDE and b <= CORE_HI]
    mu, th = model_arrays(model, bands)
    F = np.asarray(bands, dtype=float)

    true_z, true_p, true_k, true_beta = [("r", 55.0)], [("r", 210.0)], 1.30, -17.20
    h = response(F, true_k, true_z, true_p)
    meas = predict(true_beta, np.abs(h), np.angle(h), mu, th)
    w = np.ones(len(bands))

    got = fit_family(bands, ["r"], ["r"], mu, th, meas, w, ntry=40)
    hg = response(F, got["k"], got["z"], got["p"])
    dmag = float(np.max(np.abs(20 * np.log10(np.abs(hg / h)))))
    dph = float(np.max(np.abs(np.degrees(np.angle(hg / h)))))
    print("  truth : %s   beta %+.2f" % (describe(true_z, true_p, true_k), true_beta))
    print("  fitted: %s   beta %+.2f" % (describe(got["z"], got["p"], got["k"]), got["beta"]))
    print("  worst |dH| over the band: %.3f dB / %.2f deg;  d(beta) %+.3f dB;  rms %.4f dB"
          % (dmag, dph, got["beta"] - true_beta, got["rms"]))
    ok = dmag < 0.15 and dph < 2.0 and abs(got["beta"] - true_beta) < 0.15
    print("  %s\n" % ("PASS" if ok else "FAIL -- the joint fit is not trustworthy"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--csv-prefix", default="build/a3_dec_drv")
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()

    if args.selftest:
        selftest()
        return

    model = ps.load_model([d for d, _ in ps.DRIVES], args.csv_prefix)
    pedal = ps.load_pedal(args.sweep)
    bands = [b for b in ps.PROBE_BANDS if b not in EXCLUDE]
    F = np.asarray(bands, dtype=float)
    mu, th = model_arrays(model, bands)
    meas = measured(pedal, bands)
    w = np.array([1.0 if b <= CORE_HI else WEAK_W for b in bands])

    print("A3 lead fit -- element AND bleed level fitted JOINTLY, scored against the")
    print("RAW drive captures (no derived target).   sweep=%s\n" % args.sweep)
    print("Score = RMS over %d bands x 5 drives of (predicted - measured) dB, the pedal's"
          % len(bands))
    print("own totals relative to its full-clean capture. Bands >%d Hz weighted %.2f"
          % (CORE_HI, WEAK_W))
    print("(mu < 1 there, so the total is bleed-dominated); 320 Hz excluded (GAP #2).\n")

    results = []
    for label, kz, kp, fix_k in FAMILIES:
        r = fit_family(bands, kz, kp, mu, th, meas, w, fix_k=fix_k)
        r["label"] = label
        results.append(r)
        h = response(F, r["k"], r["z"], r["p"])
        r["h"] = h
        print("  %-40s rms %6.3f dB   beta %+6.2f   %s"
              % (label, r["rms"], r["beta"],
                 describe(r["z"], r["p"], r["k"]) if kz or kp else "k=%.3f" % r["k"]))

    base = results[0]
    best = min(results[1:], key=lambda r: r["rms"])

    print("\n\nHOW MUCH IS LEFT FOR AN ELEMENT TO DO?")
    print("  no element at all (H = 1, beta free): %.3f dB" % base["rms"])
    print("  best causal element found           : %.3f dB  (%s)" % (best["rms"], best["label"]))
    print("  improvement                         : %.3f dB" % (base["rms"] - best["rms"]))

    orc = oracle(bands, mu, th, meas, best["beta"])
    orms = float(np.sqrt(np.sum(w * np.array([o[2] for o in orc]) ** 2) / np.sum(w)))
    print("  ORACLE (per-band s and phase free, no causality): %.3f dB" % orms)
    print("\n  The oracle is the floor set by the DATA. A family close to it is limited")
    print("  by the measurements; one far above it is limited by its own order.")

    print("\n\nPER BAND -- residual dB, and what the element is actually doing.\n")
    pb_base = per_band(base["beta"], np.abs(base["h"]), np.angle(base["h"]), mu, th, meas)
    pb_best = per_band(best["beta"], np.abs(best["h"]), np.angle(best["h"]), mu, th, meas)
    pb_clean = clean_side_test(bands, mu, th, meas, w, base["beta"])
    print("%6s %8s %9s %9s %9s %9s %9s %9s %9s"
          % ("f", "mu(noon)", "no elem", "clean?", "element", "oracle", "|H| dB", "arg H", "orc phi"))
    for i, b in enumerate(bands):
        print("%6d %8.2f %9.2f %9.2f %9.2f %9.2f %9.1f %9.1f %9.1f"
              % (b, mu[i][2], pb_base[i], pb_clean[i], pb_best[i], orc[i][2],
                 20 * math.log10(abs(best["h"][i])),
                 math.degrees(np.angle(best["h"][i])), orc[i][1]))

    print("\n  'clean?' = best POSSIBLE per-band residual if the fix were on the CLEAN/bleed")
    print("  side instead of the OD side (a per-band constant dB offset, maximally generous")
    print("  to that hypothesis -- see clean_side_test()'s docstring for why this is the right")
    print("  test: a clean-side correction cannot vary by DRIVE, so this is its ceiling).")
    print("  If 'clean?' ~= 'no elem', the clean side cannot do ANY better than doing nothing --")
    print("  the defect is drive-dependent within-band and only an OD-side element (which")
    print("  multiplies mu_d, itself drive-dependent) can reproduce that shape.")
    print("\n  'orc phi' is the phase an unconstrained element would use at that band.")
    print("  Where 'element' tracks 'oracle', the network is doing all the data allows.")
    print("  Where 'no elem' is already at 'oracle', there is nothing there to fix.")

    # ---- the verdict, computed ------------------------------------------------
    gain = base["rms"] - best["rms"]
    headroom = best["rms"] - orms
    print("\n\nVERDICT (computed from the numbers above, not narrated).")
    print("  element buys %.3f dB; it still sits %.3f dB above the oracle floor."
          % (gain, headroom))
    if gain < 0.10:
        print("  ⛔ DO NOT BUILD IT. After trebleC7 the two-path model already explains")
        print("  the drive captures to %.3f dB with NO element at all. An added network" % base["rms"])
        print("  buys less than the take-to-take capture floor (0.144 dB, §3), so it")
        print("  would be fitting noise -- and every parameter added here has to be")
        print("  defended against a schematic that does not contain it.")
    elif gain < 0.30:
        print("  ⚠ MARGINAL. The gain is real but small against the 0.144 dB take-to-take")
        print("  floor. Gate it on the NULL before believing it, and do not ship it on")
        print("  this number alone.")
    else:
        print("  ✅ Worth carrying to the null gate: the element buys more than twice the")
        print("  take-to-take capture floor. Judge it on the migrating null, not on this.")

    print("\n  ⚠ beta moved to %+.2f dB in the joint fit (model bleed %+.2f). It is fitted"
          % (best["beta"], model[0.50][40][2]))
    print("  HERE, jointly with the element -- fixing it first has no fixed point, because")
    print("  the phase an element must supply is itself a function of beta (session 33).")

    # ---- THE GATE: the migrating null, not band-RMS --------------------------
    print("\n\nTHE NULL GATE (the pre-registered acceptance test -- NOT band-RMS).")
    print("  A3's signature is a cancellation null that MIGRATES DOWN in frequency as")
    print("  drive rises: near 40 Hz at drive 2:30, ~22-25 Hz by max (session 29). A")
    print("  candidate that lowers band-RMS without moving the null has not fixed this.")
    print("  Below: the deepest band and its depth, per drive, for the pedal and for")
    print("  each model. Depth is dB relative to the pedal's own full-clean capture.\n")

    def nulls(tab):
        out = []
        for d in range(tab.shape[1]):
            i = int(np.argmin(tab[:, d]))
            out.append((bands[i], tab[i, d]))
        return out

    lo_band = [i for i, b in enumerate(bands) if b <= CORE_HI]
    sub = np.array(lo_band)
    # EVERY family is gated, not just the band-RMS winner: the gate is the
    # acceptance test, so the right candidate is the SIMPLEST one that passes it,
    # not the one with the lowest RMS. (The 3z/3p winner parks a Q=20 zero/pole
    # pair on top of each other, which is an overfit signature, not a circuit.)
    rows = [("PEDAL (measured)", nulls(meas[sub]))]
    for r in results:
        rows.append(("  " + r["label"],
                     nulls(predict(r["beta"], np.abs(r["h"]), np.angle(r["h"]), mu, th)[sub])))
    print("  %-40s %s" % ("", "".join("%16s" % ("drive %.2f" % d) for d, _ in ps.DRIVES)))
    for label, ns in rows:
        print("  %-40s %s" % (label, "".join("%9d Hz%5.0f" % (f, v) for f, v in ns)))

    ped = rows[0][1]
    print("\n  %-40s %8s %8s %8s" % ("", "null f", "null dB", "verdict"))
    print("  %-40s %8s %8s" % ("", "match", "worst", ))
    for label, ns in rows[1:]:
        fmatch = sum(1 for i in range(len(ns)) if ns[i][0] == ped[i][0])
        dworst = max(abs(ns[i][1] - ped[i][1]) for i in range(len(ns)))
        ok = fmatch >= 4 and dworst <= 3.0
        print("  %-40s %6d/5 %8.1f   %s"
              % (label, fmatch, dworst, "PASS" if ok else "fail"))
    print("\n  'null f match' = drives where the deepest band is the SAME as the pedal's;")
    print("  'null dB worst' = largest depth error over the five drives. A candidate must")
    print("  put the null in the right place AND at the right depth -- right place at the")
    print("  wrong depth is still a magnitude error.")

    ped_n = [f for f, _ in rows[0][1]]
    ele_n = [f for f, _ in rows[-1][1]]
    base_n = [f for f, _ in rows[1][1]]
    print("\n  null frequency, 2:30 -> max:  pedal %d -> %d Hz | no element %d -> %d | "
          "element %d -> %d" % (ped_n[3], ped_n[4], base_n[3], base_n[4], ele_n[3], ele_n[4]))
    migrates = ele_n[4] <= ele_n[3]
    ped_migrates = ped_n[4] <= ped_n[3]
    print("  pedal's null migrates DOWN with drive: %s;  candidate's: %s"
          % (ped_migrates, migrates))
    if not ped_migrates:
        print("  ⚠ The MEASURED null does not migrate down over these bands at this sweep")
        print("  level -- so this gate cannot be applied as written here. Do not read a")
        print("  candidate PASS off it; re-derive the null's location before gating.")
    elif migrates:
        print("  ✅ GATE PASS on direction. Confirm the DEPTH too -- a null in the right")
        print("  place at the wrong depth is still a magnitude error.")
    else:
        print("  ⛔ GATE FAIL: the candidate does not reproduce the migration, whatever")
        print("  its band-RMS says. Do not ship it.")


if __name__ == "__main__":
    main()
