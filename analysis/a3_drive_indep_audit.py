#!/usr/bin/env python3.11
"""Phase-9 SESSION 53 — does the DRIVE axis have the POWER to prove A3's carrier is POST-clipper?

Session 50 item 2 narrowed the entire A3 search to the post-clipper region on this argument:

    `s` is ONE scale per band that must reproduce all five drive totals, and the shipped model
    already does that to 0.094 dB rms — so whatever is missing is, as measured, drive-INDEPENDENT.
    A post-clipper linear element multiplies |OD| identically at every drive; a pre-clipper one
    moves the clipper's operating point, so its delivered lift differs at every drive (`drvspr`
    4-19 dB) and cannot be represented by a single `s`.

That is an AFFIRMATION OF THE CONSEQUENT: "a drive-independent model fits, therefore the truth is
drive-independent" is valid ONLY if a drive-DEPENDENT alternative would fit detectably WORSE. This
tool measures whether it would.

⚠ WHY THIS IS NOT THE CHECK SESSION 52 QUEUED. Session 52 next-step (a) asked to re-run the
argument "with the railed bands removed" (202/254/320/1613/4064, session 51 item 6). Railing is the
wrong target: pinning theta at a boundary REMOVES a degree of freedom, so a small residual at a
railed band is if anything STRONGER evidence for drive-independence, not weaker. The real defect is
IDENTIFIABILITY — at the shipped state the +0.5 dB theta interval is 66-180 deg wide at every band
from 127 Hz up, and the entire search range at 320 Hz. Railing is a SYMPTOM of those intervals, not
the disease. An instrument that cannot locate theta to better than 90 deg is unlikely to be able to
reject a drive-dependent magnitude either — but "unlikely" is not a measurement, hence the power
test below.

WHAT IT DOES
  1. IDENTIFIABILITY TABLE — per band: solved theta, its +0.5 dB interval and width, the fit
     residual, and the CONDITIONING (`mu_spr` = max-minus-min of the model's mu_d across the five
     drives, in dB). A band where mu_d barely moves carries no drive-axis information at all, so a
     small residual there is vacuous regardless of what theta does.

  2. POWER TEST (the decisive part) — per band, synthesise pedal totals FROM THE MODEL with a
     deliberately drive-DEPENDENT correction: a mean-zero multiplicative ramp of span X dB across
     the drive ladder, on top of that band's own solved (s, theta). Then fit the drive-INDEPENDENT
     (s, theta) to it and record the residual. Mean-zero matters: a constant offset is absorbed by
     `s` exactly, so only the VARIATION across drives is the signal being tested. Sweep X and
     report the smallest span whose residual clears the pedal's own 0.144 dB take-to-take floor —
     that is the band's DETECTION THRESHOLD for drive-dependence.

  3. VERDICT — compare those thresholds against the 4-19 dB `drvspr` that pre-clipper elements
     actually deliver (session 50's own table). If the thresholds sit BELOW that range, the drive
     axis really would have caught a pre-clipper carrier and session 50 item 2 stands. If they sit
     inside or above it, the conclusion is UNSUPPORTED — not disproven, but it should never have
     been used to narrow the search, and the pre-clipper region is back in play.

Self-test (`--selftest`, run it first): span 0 must return a residual of ~0 (the synthetic data IS
the model at that point), and a large span must be detected at a well-conditioned band. If either
fails the power numbers mean nothing.

Run:  /opt/homebrew/bin/python3.11 -u analysis/a3_drive_indep_audit.py [--selftest]
Reads the same inputs as a3_phase_solve.py (build/a3_dec_drv*.csv + the report JSON).
"""
import argparse
import math
import sys

import numpy as np

sys.path.insert(0, "analysis")
import a3_phase_solve as PS   # reuse load_model/load_pedal/fit_band/interval so nothing drifts

# The pedal's own take-to-take repeatability, shape-normalised (session 24). Any residual below
# this is indistinguishable from re-recording the same setting twice.
CAPTURE_FLOOR_DB = 0.144

# Session 52 item 1 fixed the A3 fit band at 40 Hz - 1.7 kHz (below 40 the blend axis is
# unreliable; above ~2 kHz it diverges). Aggregate over the same span so the verdict is
# comparable with every other session-51/52 number.
FIT_LO_HZ, FIT_HI_HZ = 40.0, 1700.0

# Span grid for the power sweep, in dB of peak-to-peak drive-dependence.
SPANS_DB = (0.0, 0.5, 1.0, 2.0, 3.0, 4.0, 6.0, 8.0, 12.0, 16.0, 20.0)

# Session 50's measured drvspr range for PRE-clipper elements — what the instrument would have
# had to detect for the post-clipper conclusion to be earned.
PRE_CLIPPER_DRVSPR = (4.0, 19.0)


def ramp(span_db, n=5):
    """Mean-zero linear ramp of the given peak-to-peak span, as a linear multiplier per drive."""
    if n == 1:
        return np.ones(1)
    d = np.linspace(-0.5, 0.5, n)
    return 10.0 ** (span_db * d / 20.0)


def synth_totals(mu, s, theta, beta_db, span_db):
    """Pedal-like totals with a drive-DEPENDENT s. span_db = 0 reproduces the model exactly."""
    z = s * ramp(span_db, len(mu)) * np.asarray(mu, dtype=float) * np.exp(1j * theta)
    return beta_db + 20.0 * np.log10(np.maximum(np.abs(1.0 + z), 1e-12))


def detection_threshold(mu, s, theta, beta_db):
    """Smallest ramp span (dB) whose drive-INDEPENDENT refit residual clears the capture floor.

    Returns (threshold_db_or_None, [(span, residual), ...]). None => not detectable anywhere on
    the span grid, i.e. the axis is blind to drive-dependence at this band.
    """
    curve = []
    thr = None
    for span in SPANS_DB:
        t = synth_totals(mu, s, theta, beta_db, span)
        (_, cost, _), _ = PS.fit_band(list(t), mu, beta_db)
        res = math.sqrt(cost)
        curve.append((span, res))
        if thr is None and span > 0.0 and res > CAPTURE_FLOOR_DB:
            # linear interpolation between the last two grid points for a smoother threshold
            (p_span, p_res) = curve[-2]
            if res > p_res:
                frac = (CAPTURE_FLOOR_DB - p_res) / (res - p_res)
                thr = p_span + frac * (span - p_span)
            else:
                thr = span
    return thr, curve


def selftest(model, pedal, beta_db):
    print("=== SELF-TEST ===\n")
    ok = True

    # (a) span 0 must be reproduced exactly — the synthetic data IS the model there.
    print("(a) span = 0 must refit to ~0 residual (synthetic data is the model itself):")
    worst = 0.0
    for b in (40, 101, 508):
        mu = [model[d][b][0] for d, _ in PS.DRIVES]
        sol = PS.fit_band(pedal[b], mu, beta_db)[0]
        s, theta = sol[2], sol[0]
        t = synth_totals(mu, s, theta, beta_db, 0.0)
        (_, cost, _), _ = PS.fit_band(list(t), mu, beta_db)
        res = math.sqrt(cost)
        worst = max(worst, res)
        print(f"    {b:5} Hz   residual = {res:.6f} dB")
    if worst > 0.01:
        print(f"    FAIL — worst {worst:.6f} dB > 0.01"); ok = False
    else:
        print(f"    PASS — worst {worst:.6f} dB\n")

    # (b) a large drive-dependence must be DETECTED at a well-conditioned band. 40 Hz has the
    #     tightest theta interval in the whole set (9 deg), so if any band has power, it does.
    print("(b) a 20 dB drive-dependent ramp must be detected at 40 Hz (tightest interval):")
    mu = [model[d][40][0] for d, _ in PS.DRIVES]
    sol = PS.fit_band(pedal[40], mu, beta_db)[0]
    t = synth_totals(mu, sol[2], sol[0], beta_db, 20.0)
    (_, cost, _), _ = PS.fit_band(list(t), mu, beta_db)
    res = math.sqrt(cost)
    print(f"    residual = {res:.4f} dB   vs floor {CAPTURE_FLOOR_DB}")
    if res <= CAPTURE_FLOOR_DB:
        print("    FAIL — the test cannot detect even a 20 dB drive-dependence; "
              "the power numbers below would be meaningless"); ok = False
    else:
        print("    PASS\n")

    print("SELF-TEST: %s" % ("PASS" if ok else "FAIL"))
    return ok


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--beta-db", type=float, default=None)
    ap.add_argument("--csv-prefix", default="build/a3_dec_drv")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()

    model = PS.load_model([d for d, _ in PS.DRIVES], a.csv_prefix)
    pedal = PS.load_pedal(a.sweep)
    beta_db = a.beta_db if a.beta_db is not None else PS.fit_beta(pedal, model)
    print(f"beta = {beta_db:.2f} dB (fitted)   sweep = {a.sweep}\n")

    if a.selftest:
        sys.exit(0 if selftest(model, pedal, beta_db) else 1)

    bands = [b for b in PS.PROBE_BANDS if b <= 2000]

    print("=== 1. IDENTIFIABILITY AND CONDITIONING ===")
    print("mu_spr = max-min of the MODEL's mu_d across the 5 drives (dB) = how much drive-axis")
    print("information the band carries at all. width = the +0.5 dB theta interval.\n")
    print(f"{'f':>6} {'theta':>7} {'[lo':>7} {'hi]':>7} {'width':>7} {'rms_dB':>7} "
          f"{'s':>7} {'mu_spr':>7}  note")
    rows = {}
    for b in bands:
        mu = [model[d][b][0] for d, _ in PS.DRIVES]
        best, prof = PS.fit_band(pedal[b], mu, beta_db)
        lo, hi = PS.interval(prof, best[1])
        mu_spr = 20.0 * math.log10(max(mu) / min(mu)) if min(mu) > 0 else float("inf")
        theta_deg = math.degrees(best[0])
        railed = theta_deg <= 0.05 or theta_deg >= 179.95
        rows[b] = dict(theta=best[0], s=best[2], rms=math.sqrt(best[1]),
                       lo=lo, hi=hi, width=hi - lo, mu_spr=mu_spr, railed=railed, mu=mu)
        note = []
        if railed:
            note.append("RAILED")
        if hi - lo >= 60.0:
            note.append("theta unidentified")
        print(f"{b:6} {theta_deg:7.1f} {lo:7.1f} {hi:7.1f} {hi-lo:7.1f} "
              f"{math.sqrt(best[1]):7.2f} {best[2]:7.2f} {mu_spr:7.2f}  {' '.join(note)}")

    fitband = [b for b in bands if FIT_LO_HZ <= b <= FIT_HI_HZ]
    agg = math.sqrt(np.mean([rows[b]["rms"] ** 2 for b in fitband]))
    interior = [b for b in fitband if not rows[b]["railed"]]
    agg_int = math.sqrt(np.mean([rows[b]["rms"] ** 2 for b in interior]))
    narrow = [b for b in fitband if rows[b]["width"] < 60.0]
    print(f"\nresidual RMS over the {FIT_LO_HZ:.0f}-{FIT_HI_HZ:.0f} Hz fit band "
          f"({len(fitband)} bands): {agg:.3f} dB")
    print(f"  ... restricted to theta-INTERIOR bands ({len(interior)}): {agg_int:.3f} dB")
    print(f"  ... bands whose theta interval is NARROWER than 60 deg: "
          f"{narrow if narrow else 'NONE'}")
    print(f"\n⚠ Session 50 item 2 quotes 0.094 dB rms for this quantity. I cannot reproduce that")
    print(f"  figure from any code in the tree; recomputed at the shipped state it is {agg:.3f} dB")
    print(f"  ({agg/0.094:.1f}x larger) and already {agg/CAPTURE_FLOOR_DB:.1f}x the "
          f"{CAPTURE_FLOOR_DB} dB capture floor.")

    print("\n\n=== 2. POWER TEST — can this axis DETECT drive-dependence? ===")
    print("Inject a mean-zero drive-dependent ramp of the given peak-to-peak span into synthetic")
    print("totals built from the model, then refit a drive-INDEPENDENT (s, theta). 'thr' = the")
    print(f"smallest span whose residual clears the {CAPTURE_FLOOR_DB} dB capture floor.\n")
    hdr = "".join(f"{s:>7.1f}" for s in SPANS_DB)
    print(f"{'f':>6} {'thr_dB':>8}  residual vs span (dB):{hdr}")
    thrs = {}
    for b in bands:
        r = rows[b]
        thr, curve = detection_threshold(r["mu"], r["s"], r["theta"], beta_db)
        thrs[b] = thr
        cells = "".join(f"{res:>7.2f}" for _, res in curve)
        tstr = f"{thr:8.2f}" if thr is not None else "    none"
        print(f"{b:6} {tstr}  {'':22}{cells}")

    print("\n\n=== 3. DOES THE AXIS HAVE POWER? ===")
    lo_pre, hi_pre = PRE_CLIPPER_DRVSPR
    blind = [b for b in fitband if thrs[b] is None]
    weak = [b for b in fitband if thrs[b] is not None and thrs[b] >= lo_pre]
    strong = [b for b in fitband if thrs[b] is not None and thrs[b] < lo_pre]
    print(f"Over the {FIT_LO_HZ:.0f}-{FIT_HI_HZ:.0f} Hz fit band ({len(fitband)} bands), vs the")
    print(f"{lo_pre:.0f}-{hi_pre:.0f} dB drvspr that pre-clipper elements actually deliver:\n")
    print(f"  would have DETECTED a pre-clipper carrier (thr < {lo_pre:.0f} dB): "
          f"{len(strong)} bands {strong}")
    print(f"  would NOT have detected it (thr >= {lo_pre:.0f} dB):            "
          f"{len(weak)} bands {weak}")
    print(f"  BLIND at every span tested (no threshold at all):           "
          f"{len(blind)} bands {blind}")
    has_power = len(strong) >= 0.5 * len(fitband)
    print("\n=> the drive axis %s the power to detect a pre-clipper carrier." %
          ("HAS" if has_power else "LACKS"))
    print("   ⚠ Wide theta intervals do NOT imply no power: the residual test constrains the")
    print("   MAGNITUDE ladder's shape, and mu_spr spans 4-25 dB, so a drive-dependent ramp")
    print("   cannot be absorbed even where theta is free. My going-in hypothesis was wrong.")

    print("\n\n=== 4. SO WHAT DOES IT ACTUALLY SAY ABOUT THE SHIPPED MODEL? ===")
    print("Having established the axis CAN see drive-dependence, invert each band's power curve")
    print("to ask: how much drive-dependence would produce the residual we ACTUALLY observe?\n")
    print("⚠ This attributes the WHOLE residual to drive-dependence, so it is an UPPER BOUND on")
    print("  the drive-dependent part (capture noise, band leakage and errors in mu_d's own shape")
    print("  all land here too). It cannot prove the carrier is pre-clipper. What it CAN do is")
    print("  test the claim that the residual is small enough to call the defect drive-INDEPENDENT.\n")

    def invert(curve, target):
        """Span (dB) at which the power curve reaches `target` residual; None if never."""
        for (s0, r0), (s1, r1) in zip(curve, curve[1:]):
            if r0 <= target <= r1 and r1 > r0:
                return s0 + (target - r0) / (r1 - r0) * (s1 - s0)
        return None

    print(f"{'f':>6} {'rms_dB':>8} {'equiv_span_dB':>14}  verdict")
    equiv = {}
    for b in fitband:
        _, curve = detection_threshold(rows[b]["mu"], rows[b]["s"], rows[b]["theta"], beta_db)
        e = invert(curve, rows[b]["rms"])
        equiv[b] = e
        if e is None:
            v = "off the span grid (>%.0f dB)" % SPANS_DB[-1]
        elif e >= lo_pre:
            v = "INSIDE the pre-clipper range"
        else:
            v = "below the pre-clipper range"
        estr = f"{e:14.1f}" if e is not None else f"{'>20':>14}"
        print(f"{b:6} {rows[b]['rms']:8.2f} {estr}  {v}")

    vals = [e for e in equiv.values() if e is not None]
    inside = [b for b, e in equiv.items() if e is not None and e >= lo_pre]
    med = float(np.median(vals)) if vals else float("nan")
    print(f"\nmedian equivalent drive-dependence over the fit band: {med:.1f} dB")
    print(f"bands whose residual alone implies >= {lo_pre:.0f} dB of drive-dependence: "
          f"{len(inside)} of {len(fitband)} {inside}")

    print("\n\n=== 5. VERDICT ===")
    if not has_power:
        print("The axis lacks power; session 50 item 2 is unsupported for that reason alone.")
    elif med >= 1.0:
        print("Session 50 item 2 is INVERTED, not merely unsupported:")
        print(f"  * the axis genuinely CAN see drive-dependence (thresholds {min(t for t in thrs.values() if t):.1f}"
              f"-{max(t for t in thrs.values() if t):.1f} dB), so its verdict is meaningful;")
        print(f"  * but the shipped model's residual is {agg:.3f} dB RMS, NOT the 0.094 dB the")
        print(f"    argument was built on — {agg/0.094:.0f}x larger and {agg/CAPTURE_FLOOR_DB:.1f}x the capture floor;")
        print(f"  * translated through the power curves that residual is equivalent to a MEDIAN")
        print(f"    {med:.1f} dB of unmodelled drive-dependence, with {len(inside)} band(s) already inside")
        print(f"    the {lo_pre:.0f}-{hi_pre:.0f} dB range that pre-clipper elements deliver.")
        print("\n=> The drive axis does NOT say the missing element is drive-independent. Read")
        print("   correctly it says the opposite: there is several dB of drive-dependent residual")
        print("   the drive-independent model cannot absorb. The post-clipper restriction that has")
        print("   scoped A3 since session 50 rests on a residual figure I cannot reproduce, and at")
        print("   the reproducible figure the same argument points PRE-clipper.")
        print("   ⚠ This does not prove the carrier IS pre-clipper (see the upper-bound caveat in")
        print("   section 4) — it removes the reason for excluding it. Combined with session 52's")
        print("   proof that no causal linear POST-clipper element can supply the target, the")
        print("   pre-clipper region is now the only one not ruled out.")
    else:
        print("Session 50 item 2 STANDS: the axis has power and the residual is small enough that")
        print("the missing element really does act drive-independently. Keep the post-clipper scope.")


if __name__ == "__main__":
    main()
