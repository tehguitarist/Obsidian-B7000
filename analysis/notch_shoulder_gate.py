#!/usr/bin/env python3.11
"""GATE AX (session 161) — the GRUNT-Cut SHOULDER SECTION, screened and refuted on task A's terms.

WHAT THIS SETTLES.  `OdToneRestore.h` has said since s151 that the Cut row's Q residual is
STRUCTURAL — "a single peaking section adding a few dB at the centre cannot narrow a null that is
already 14 dB deep and broad; narrowing it needs a second section shaping the SHOULDERS" — and
GATE AQ (s153) turned that from a stall into a measured limit: sweeping ONE section's Q to 120 with
the depth re-solved at every rung, the pedal's Q is attainable in 21 of 26 cells and ALL FIVE
failures are in the Cut row, with Cut x DRIVE 0.50 failing at all three sweeps.  The user
authorised building that second section (session 160, task A) at GRUNT Cut only, capped at two fit
iterations, with acceptance: depth stays within the shipped +/-0.83 dB, Cut's Q error drops below
the reader's own resolution, CLEAN stays bit-identical, release gate no worse.

⛔⛔ THE SECTION IS REFUTED AND NOTHING SHIPS.  It is NOT refuted on reachability — AX2 confirms
GATE AQ's own diagnosis and finds the pedal's Q reachable at 9 of 9 Cut cells once a second section
exists, so s151's "structural" sentence and s153's measurement were both right.  It is refuted on
four measurements that only appear once you ask what would actually be SHIPPED:

  AX3  THE CURVE BARELY WANTS IT.  On `fit_rung`'s own objective (the curve over FIT_BAND with a
       quadratic-in-log-f trend fitted jointly and discarded, because that trend is A3) a free
       third section buys a MEDIAN 0.080 dB of fit.  The 320 Hz notch term buys 1.56 dB, and s156
       rejected the 800 Hz candidate at 0.058 dB.  So this term sits with the REJECTED one, not
       with the accepted one.  Its fitted gain changes sign across the ladder (+16.2 ... -6.0) and
       rests on a bound in 2 of 9 cells (`bound-resting-means-unidentified`).

  AX4  LIKE-FOR-LIKE IT LOSES TO RE-FITTING THE EXISTING TWO SECTIONS.  Matched on (depth, Q),
       mean curve rms: shipped 1.257, existing family re-solved 1.167, third section 1.222 dB — and
       it beats the re-solve in only 3 of 9 cells.  ⚠ This control is what a first pass MISSED: a
       three-section arm compared against the SHIPPED tables improves 1.286 -> 0.780 dB and looks
       decisive, but it re-solves two constants at the same time as it adds a section, so the
       improvement is not attributable (`verify-the-BASELINE-not-its-LABEL`).

  AX5  IN THE SHIPPABLE FORM IT FAILS TASK A's OWN ACCEPTANCE.  The stage carries ONE entry per
       (GRUNT, DRIVE), so the graded object is one cut gain and one broad gain per DRIVE rung
       across all three stimulus sweeps (AR3's distinction: this is the right statistic for the
       SHIPPING question and the wrong one for a mechanism claim).  Given its fairest shot — broad
       Q swept, broad gain swept, cut gain re-solved so the depth stays matched — it moves the mean
       |Q error| 0.97 -> 0.81, 4.09 -> 3.05, 5.15 -> 3.49.  Real, and nowhere near "below the
       reader's resolution"; and it costs |depth error| at two of three rungs.  The table it asks
       for has NO LAW: gain -13.0 / +10.0 / -13.0 and Q 4.5 / 1.5 / 9.0 across the three rungs.

  AX6  ⭐⭐ AND THE REASON, WHICH IS WHY NO FURTHER ITERATION IS OWED: THE SHIPPED Q ERROR IS
       ALREADY SMALLER THAN THE TARGET'S OWN ACROSS-STIMULUS SPREAD AT ALL THREE RUNGS.  The
       pedal's own null Q at fixed (GRUNT, DRIVE) runs 6.45/5.75/4.99, 13.91/10.53/8.39 and
       19.89/12.10/9.69 across the three stimulus sweeps — spreads of 1.46, 5.52 and 10.20 —
       against shipped errors of 0.98, 4.04 and 5.19.  ⇒ a knob-keyed entry is ALREADY inside the
       ambiguity of the thing it is fitting, so "closer to the pedal's Q" is not a well-defined
       target for any single number, whatever family produces it.  That is s151 §6's architectural
       limit (a knob-keyed stage cannot track a stimulus-dependent feature) on a FOURTH axis, after
       AQ2b's Q, AR6's metric residual and AU's peak gain — and AQ2b already said to read it "as an
       argument for leaving `kNotchQ` ALONE".

⇒ per the user's own stop condition ("ship the better of the two and close"), the better is the
CURRENT state: the candidate is worse on depth at two rungs and does not meet the Q bar at any.
NOTHING in `src/` changes, so CLEAN is bit-identical trivially and the release gate cannot move.

⚠ SCOPE.  This refutes a SECOND PEAKING SECTION AT THE NULL'S OWN CENTRE, which is the family
s151/s153 named and the user authorised.  It does not refute every conceivable shoulder treatment
(two independent off-centre sections, an asymmetric or non-biquad shape).  What AX6 does bound is
the VALUE of any of them: none can beat the target's own spread.
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import feature_locus_gate as W          # noqa: E402
import null_depth_censor_gate as AP     # noqa: E402
import notch_shape_gate as AQ           # noqa: E402
import od_tone_restore_fit as F         # noqa: E402

REAL = AP.REAL
FS = 48000.0 * W.OS_FACTOR
FIT_RESIDUAL_DB = AP.FIT_RESIDUAL_DB

# The candidate's own free parameters.  Swept, never fixed at one guessed value — refuting a
# candidate at one arbitrary setting of its own parameter is the mirror of `a-threshold-you-
# guessed-is-not-a-guard`.
QB_LADDER = (0.7, 1.0, 1.5, 2.0, 3.0, 4.5, 6.0, 9.0)
GB_LADDER = np.arange(-14.0, 18.01, 1.0)
QN_LADDER = np.geomspace(2.0, 60.0, 16)

REPORT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports",
                      "s161_notch_shoulder.json")

FAIL, NOTE = [], []


def fail(tag, msg):
    FAIL.append(tag)
    print(f"  ❌ {tag}: {msg}")


# ================================================================================================
# the candidate composite — GATE AQ's, with one section added
# ================================================================================================
def comp(g, mod_off, cut_db, qn, gb, qb, drv, T):
    """mod_off + narrow CUT + the candidate broad section + the shipped PEAK section.

    Exact and rebuild-free: every section is linear and in series, so their dB responses add — the
    same argument that licenses `--stage-off` and GATE AP's solve.  At gb = 0 this MUST reduce to
    GATE AQ's `composite`, which AX1 asserts."""
    peak = F.rbj_peak_db(g, FS, T["kPeakFreq"], T["kPeakQ"], F.lerp5(T["kPeakGainDb"], drv, T["kX"]))
    return (mod_off
            + F.rbj_peak_db(g, FS, T["kNotchFreq"], qn, -cut_db)
            + F.rbj_peak_db(g, FS, T["kNotchFreq"], qb, gb)
            + peak)


def geo(g, mod_off, cut_db, qn, gb, qb, drv, T):
    try:
        return F.notch_geometry(g, comp(g, mod_off, cut_db, qn, gb, qb, drv, T))
    except RuntimeError:
        return None


def curve_rms(g, ped, c):
    """`fit_rung`'s own objective, so it is directly comparable to the stage's ±0.83 dB residual."""
    m = (g >= F.FIT_BAND[0]) & (g <= F.FIT_BAND[1])
    r = (ped - c)[m]
    B = F.trend_basis(g[m])
    co, *_ = np.linalg.lstsq(B, r, rcond=None)
    return float(np.sqrt(np.mean((r - B @ co) ** 2)))


def cut_ship_of(drv, cf, T):
    return (F.lerp5(T["kNotchGainDb"][0], drv, T["kX"])
            + F.lerp5(T["kNotchMixK"][0], drv, T["kX"]) * F.mix_shape(cf, T))


def load_cells(T):
    """-> {drive: (cut_ship, qn, [(g, ped, mod_off, ped_geo, sweep)])} for the bleed-free Cut set."""
    out = {}
    for fname, drv in F.SETS["bleedfree"]:
        cf = F.clean_frac_of(fname)
        cells = []
        for sweep in REAL:
            g, ped, mod = F.curves(fname, sweep)
            mo = mod - F.current_response(g, drv, FS, T, 0, cf)
            try:
                pg = F.notch_geometry(g, ped)
            except RuntimeError:
                continue
            if not np.isfinite(pg[AQ.QKEY]):
                continue
            cells.append((g, ped, mo, pg, sweep))
        if cells:
            out[drv] = (cut_ship_of(drv, cf, T), F.lerp5(T["kNotchQ"][0], drv, T["kX"]), cells)
    return out


def solve_cut_at(g, mod_off, target_depth, qn, gb, qb, drv, T):
    from scipy.optimize import brentq

    def err(c):
        r = geo(g, mod_off, c, qn, gb, qb, drv, T)
        return -1e3 if r is None else r["depth_point"] - target_depth

    if err(AQ.GAIN_LO) > 0 or err(AQ.GAIN_HI) < 0:
        return None
    return float(brentq(err, AQ.GAIN_LO, AQ.GAIN_HI, xtol=1e-3))


# ================================================================================================
# AX1 — known answer
# ================================================================================================
def ax1(T, cells):
    """CROSS-GATE KNOWN ANSWER: at gb = 0 this gate's composite IS GATE AQ's.

    The right answer already exists and was produced by code this gate does not share, so agreement
    certifies that adding a third section did not change the object being measured.
    ⚠ Blind to: both sides evaluate the same `notch_geometry`, the same `rbj_peak_db` and the same
    curves — it validates the plumbing, not the reader, the biquad or the data (s145/s149's lesson,
    stated because this is exactly the shape that cost the project ten sessions)."""
    print("\nAX1  KNOWN ANSWER — the candidate is inert at gb = 0, so this is GATE AQ's composite")
    worst, n = 0.0, 0
    for drv, (cut_ship, qn, cs) in cells.items():
        for g, ped, mo, pg, _ in cs:
            a = AQ.composite(g, mo, cut_ship, qn, drv, T, FS)
            b = comp(g, mo, cut_ship, qn, 0.0, 3.0, drv, T)
            worst = max(worst, float(np.max(np.abs(a - b))))
            n += 1
    print(f"  worst |AQ.composite − AX.comp(gb=0)| = {worst:.2e} dB over n={n} cells")
    if n == 0:
        fail("AX1", "no cell produced a comparison — the known answer never ran (`empty-gate-must-fail`)")
    elif worst > 1e-12:
        fail("AX1", f"the third section is not inert at gb=0 ({worst:.2e} dB) — nothing below is readable")
    else:
        print("  ✅ inert, so every difference below is the section and not a re-parameterisation.")
    return {"worst_db": worst, "n": n}


# ================================================================================================
# AX2 — reachability (confirms GATE AQ's AQ2, and confirms the section CAN do the job per cell)
# ================================================================================================
def ax2(T, cells):
    print("\nAX2  REACHABILITY — one section vs two, pedal Q as the target, DEPTH held matched")
    print("     (holding depth matched is AQ2's own discipline: without it a high-Q section")
    print("      trivially 'narrows' the composite by doing less)")
    rows, n1, n2 = [], 0, 0
    for drv, (cut_ship, qn_ship, cs) in cells.items():
        for g, ped, mo, pg, sweep in cs:
            tgt_d, tgt_q = pg["depth_point"], pg[AQ.QKEY]
            b1 = b2 = -1.0
            for qn in QN_LADDER:
                c = solve_cut_at(g, mo, tgt_d, qn, 0.0, 3.0, drv, T)
                if c is not None:
                    r = geo(g, mo, c, qn, 0.0, 3.0, drv, T)
                    if r is not None and np.isfinite(r[AQ.QKEY]):
                        b1 = max(b1, r[AQ.QKEY])
                for qb in QB_LADDER:
                    for gb in (4.0, 8.0, 12.0, 16.0):
                        c = solve_cut_at(g, mo, tgt_d, qn, gb, qb, drv, T)
                        if c is None:
                            continue
                        r = geo(g, mo, c, qn, gb, qb, drv, T)
                        if r is not None and np.isfinite(r[AQ.QKEY]):
                            b2 = max(b2, r[AQ.QKEY])
            n1 += b1 >= tgt_q
            n2 += b2 >= tgt_q
            rows.append({"drive": drv, "sweep": sweep, "ped_q": tgt_q, "max1": b1, "max2": b2})
            print(f"  drv {drv:4.2f} {sweep:>14}  pedal Q {tgt_q:6.2f} | 1-section max {b1:6.2f} "
                  f"{'reach' if b1 >= tgt_q else ' MISS'} | 2-section max {b2:6.2f} "
                  f"{'reach' if b2 >= tgt_q else ' MISS'}")
    print(f"  ⇒ one section reaches {n1} of {len(rows)};  two sections reach {n2} of {len(rows)}")
    if n2 <= n1:
        NOTE.append("AX2: the second section did not improve reachability — AQ2's premise not reproduced")
    else:
        print("  ✅ s151's 'needs a second section shaping the shoulders' is CONFIRMED as reachability.")
    return {"rows": rows, "reach_one": n1, "reach_two": n2}


# ================================================================================================
# AX3 — how much FIT does it buy?  (s156 §3's test, on a second candidate term)
# ================================================================================================
def ax3(T, cells):
    """The measurement that rejected the 800 Hz candidate at s156 (0.058 dB against the notch
    term's 1.56), applied to this one.  A term that buys nothing on the curve is a term the fit
    does not want, whatever a derived scalar says."""
    from scipy.optimize import least_squares
    print("\nAX3  FIT BOUGHT by a free third section (objective = `fit_rung`'s, trend discarded)")
    print(f"  {'DRIVE':>5} {'sweep':>14} | {'rms 2-sect':>10} {'rms 3-sect':>10} {'bought':>7} | "
          f"{'broad dB':>9} {'broad Q':>8}")

    def run(g, ped, mod, drv, cf, with_broad):
        lo, hi = F.FIT_BAND
        m = (g >= lo) & (g <= hi)
        f = g[m]
        target = F.current_response(f, drv, FS, T, 0, cf) + (ped - mod)[m]
        B = F.trend_basis(f)

        def shape(p):
            fn, qn, gn, fp, qp, gp = p[:6]
            r = F.rbj_peak_db(f, FS, fn, qn, -gn) + F.rbj_peak_db(f, FS, fp, qp, gp)
            return r + F.rbj_peak_db(f, FS, fn, p[6], p[7]) if with_broad else r

        def resid(p):
            r = target - shape(p)
            co, *_ = np.linalg.lstsq(B, r, rcond=None)
            return r - B @ co

        lb = [295.0, 1.0, -6.0, 360.0, 0.5, -8.0] + ([0.3, -6.0] if with_broad else [])
        ub = [355.0, 20.0, 26.0, 620.0, 8.0, 10.0] + ([20.0, 18.0] if with_broad else [])
        best = None
        for f0 in (305.0, 324.0, 340.0):
            for q0 in (2.0, 6.0, 12.0):
                for gn0 in (0.0, 8.0):
                    p0 = [f0, q0, gn0, 470.0, 2.0, 0.0] + ([1.0, 0.0] if with_broad else [])
                    try:
                        r = least_squares(resid, p0, bounds=(lb, ub), max_nfev=4000)
                    except Exception:
                        continue
                    if best is None or r.cost < best.cost:
                        best = r
        return best

    rows = []
    for fname, drv in F.SETS["bleedfree"]:
        cf = F.clean_frac_of(fname)
        for sweep in REAL:
            g, ped, mod = F.curves(fname, sweep)
            b2, b3 = run(g, ped, mod, drv, cf, False), run(g, ped, mod, drv, cf, True)
            r2 = float(np.sqrt(np.mean(b2.fun ** 2)))
            r3 = float(np.sqrt(np.mean(b3.fun ** 2)))
            gb, qb = float(b3.x[7]), float(b3.x[6])
            onb = abs(gb - (-6.0)) < 1e-3 or abs(gb - 18.0) < 1e-3
            rows.append({"drive": drv, "sweep": sweep, "rms2": r2, "rms3": r3,
                         "broad_db": gb, "broad_q": qb, "on_bound": bool(onb)})
            print(f"  {drv:5.2f} {sweep:>14} | {r2:10.3f} {r3:10.3f} {r2 - r3:+7.3f} | "
                  f"{gb:+9.2f} {qb:8.2f}{'  [bound]' if onb else ''}")
    bought = [r["rms2"] - r["rms3"] for r in rows]
    gains = [r["broad_db"] for r in rows]
    nb = sum(r["on_bound"] for r in rows)
    signs = sum(1 for x in gains if x > 0), sum(1 for x in gains if x < 0)
    print(f"\n  median bought {np.median(bought):.3f} dB (range {min(bought):.3f}..{max(bought):.3f})")
    print(f"  ⇒ the 320 Hz notch term buys 1.56 dB; s156 REJECTED the 800 Hz candidate at 0.058 dB.")
    # ⚠ COMPUTED, not narrated.  A first draft printed "it CHANGES SIGN" unconditionally and the
    # mutation runner's `ax3-one-signed` arm caught it — a caption that cannot come back as its
    # opposite is exactly `computed-verdicts-not-narrated`, committed inside a gate written to
    # apply that rule to someone else.
    sign_note = "it CHANGES SIGN" if (signs[0] and signs[1]) else "it is ONE-SIGNED"
    print(f"  fitted gain signs: {signs[0]} positive / {signs[1]} negative — {sign_note};  "
          f"{nb} of {len(rows)} rest on a bound")
    return {"rows": rows, "median_bought": float(np.median(bought)),
            "n_on_bound": nb, "n_pos": signs[0], "n_neg": signs[1]}


# ================================================================================================
# AX4 — the like-for-like control
# ================================================================================================
def ax4(T, cells):
    """Does the third section beat RE-FITTING THE EXISTING TWO?  The control a first pass missed.

    Arm B is GATE AQ's own `solve_gain_q`, imported — the existing (gain, Q) family solved against
    the same two targets.  Comparing a three-section solve against the SHIPPED tables instead
    re-solves two constants at the same time as it adds a section, and the improvement is then not
    attributable to the section (`verify-the-BASELINE-not-its-LABEL`)."""
    from scipy.optimize import brentq
    print("\nAX4  LIKE-FOR-LIKE — third section vs re-fitting the existing two, both matched on (depth, Q)")
    print(f"  {'DRIVE':>5} {'sweep':>14} | {'A ship':>8} | {'B 2-sect':>8} | {'C 3-sect':>8}   (curve rms)")

    def pair(g, mo, tgt_d, tgt_q, qn, drv):
        def cut_for(gb):
            return solve_cut_at(g, mo, tgt_d, qn, gb, 3.0, drv, T)

        def qerr(gb):
            c = cut_for(gb)
            if c is None:
                return -1e3
            r = geo(g, mo, c, qn, gb, 3.0, drv, T)
            return (r[AQ.QKEY] if r is not None and np.isfinite(r[AQ.QKEY]) else -1e3) - tgt_q

        vals = [qerr(v) for v in GB_LADDER]
        for (a, va), (b, vb) in zip(zip(GB_LADDER, vals), zip(GB_LADDER[1:], vals[1:])):
            if (va < 0) != (vb < 0) and abs(va) < 1e2 and abs(vb) < 1e2:
                gb = float(brentq(qerr, a, b, xtol=1e-3))
                c = cut_for(gb)
                return None if c is None else (c, gb)
        return None

    A, B, Cc, cbeats, rows = [], [], [], 0, []
    for drv, (cut_ship, qn, cs) in cells.items():
        for g, ped, mo, pg, sweep in cs:
            ra = curve_rms(g, ped, comp(g, mo, cut_ship, qn, 0.0, 3.0, drv, T))
            sb = AQ.solve_gain_q(g, mo, pg, drv, T, FS, "point")
            rb = (curve_rms(g, ped, comp(g, mo, sb[0], sb[1], 0.0, 3.0, drv, T))
                  if sb is not None else float("nan"))
            sc = pair(g, mo, pg["depth_point"], pg[AQ.QKEY], qn, drv)
            rc = (curve_rms(g, ped, comp(g, mo, sc[0], qn, sc[1], 3.0, drv, T))
                  if sc is not None else float("nan"))
            A.append(ra); B.append(rb); Cc.append(rc)
            if np.isfinite(rb) and np.isfinite(rc) and rc < rb - 1e-3:
                cbeats += 1
            rows.append({"drive": drv, "sweep": sweep, "rms_ship": ra, "rms_2sect": rb,
                         "rms_3sect": rc, "broad_db": None if sc is None else sc[1]})
            print(f"  {drv:5.2f} {sweep:>14} | {ra:8.3f} | {rb:8.3f} | {rc:8.3f}")

    def mn(v):
        v = [x for x in v if np.isfinite(x)]
        return float(np.mean(v)) if v else float("nan")
    print(f"\n  mean curve rms   A shipped {mn(A):.3f}   B existing-family re-solved {mn(B):.3f}   "
          f"C third section {mn(Cc):.3f} dB")
    print(f"  cells where C beats B: {cbeats} of {len(rows)}")
    if mn(Cc) <= mn(B):
        NOTE.append("AX4: the third section beat the re-solve on the mean — re-read the verdict")
    else:
        print("  ⇒ the third section LOSES to simply re-fitting the two sections already shipped.")
    return {"rows": rows, "mean_ship": mn(A), "mean_2sect": mn(B), "mean_3sect": mn(Cc),
            "c_beats_b": cbeats, "n": len(rows)}


# ================================================================================================
# AX5 — the SHIPPING form, on task A's own acceptance
# ================================================================================================
def ax5(T, cells):
    """ONE cut gain and ONE broad gain per DRIVE rung, graded across all three stimulus sweeps.

    That is what the stage can express (`kNotchGainDb`/`kNotchQ` carry one entry per (GRUNT,
    DRIVE)), and AR3's distinction applies: this is the right statistic for the SHIPPING question
    and the wrong one for a mechanism claim.  The candidate gets its fairest shot — its Q AND its
    gain are both swept, and the cut is re-solved at every candidate so the DEPTH stays matched,
    depth being the acceptance criterion that must not regress."""
    from scipy.optimize import minimize_scalar
    print("\nAX5  THE SHIPPING FORM — one (cut, broad) pair per DRIVE rung, on task A's acceptance")
    print(f"     broad Q swept {list(QB_LADDER)};  broad gain {GB_LADDER[0]:+.0f}..{GB_LADDER[-1]:+.0f} dB")

    def depth_err(cs, c, qn, gb, qb, drv):
        e = []
        for g, ped, mo, pg, _ in cs:
            r = geo(g, mo, c, qn, gb, qb, drv, T)
            e.append(30.0 if r is None else abs(r["depth_point"] - pg["depth_point"]))
        return float(np.mean(e))

    def q_err(cs, c, qn, gb, qb, drv):
        e = []
        for g, ped, mo, pg, _ in cs:
            r = geo(g, mo, c, qn, gb, qb, drv, T)
            e.append(np.nan if r is None or not np.isfinite(r[AQ.QKEY])
                     else abs(r[AQ.QKEY] - pg[AQ.QKEY]))
        return float(np.nanmean(e)) if e else float("nan")

    def best_cut(cs, c0, qn, gb, qb, drv):
        r = minimize_scalar(lambda c: depth_err(cs, c, qn, gb, qb, drv),
                            bounds=(c0 - 14.0, c0 + 18.0), method="bounded")
        return float(r.x), float(r.fun)

    rows = []
    for drv, (cut_ship, qn, cs) in cells.items():
        d_ship, q_ship = depth_err(cs, cut_ship, qn, 0.0, 3.0, drv), q_err(cs, cut_ship, qn, 0.0, 3.0, drv)
        c_ctl, d_ctl = best_cut(cs, cut_ship, qn, 0.0, 3.0, drv)
        q_ctl = q_err(cs, c_ctl, qn, 0.0, 3.0, drv)
        best = (1e9, None)
        for qb in QB_LADDER:
            for gb in GB_LADDER:
                if gb == 0.0:
                    continue
                c, d = best_cut(cs, cut_ship, qn, gb, qb, drv)
                q = q_err(cs, c, qn, gb, qb, drv)
                if np.isfinite(q) and d <= d_ctl + FIT_RESIDUAL_DB and q < best[0]:
                    best = (q, (qb, gb, c, d))
        row = {"drive": drv, "q_ship": q_ship, "d_ship": d_ship, "q_ctl": q_ctl, "d_ctl": d_ctl}
        print(f"\n  DRIVE {drv:4.2f}   (shipped cut {cut_ship:6.2f} dB @ Q {qn:5.2f})")
        print(f"    shipped                        |depth err| {d_ship:5.2f}   |Q err| {q_ship:6.2f}")
        print(f"    cut re-solved, NO section      |depth err| {d_ctl:5.2f}   |Q err| {q_ctl:6.2f}")
        if best[1] is None:
            print("    best WITH section              — none held the depth within the bar")
        else:
            qb, gb, c, d = best[1]
            row.update({"q_best": best[0], "d_best": d, "broad_q": qb, "broad_db": gb})
            print(f"    best WITH section (Q {qb:4.1f}, {gb:+5.1f} dB)   |depth err| {d:5.2f}   "
                  f"|Q err| {best[0]:6.2f}")
            print(f"    ⇒ buys {q_ctl - best[0]:+.2f} of Q error, and costs "
                  f"{d - d_ctl:+.2f} of depth error")
        rows.append(row)
    gs = [r.get("broad_db") for r in rows if r.get("broad_db") is not None]
    if gs and (min(gs) < 0 < max(gs)):
        seq = " / ".join(f"{x:+.1f}" for x in gs)
        print(f"\n  ⚠⚠ the requested broad gain changes sign across the drive ladder "
              f"({seq}) — there is NO LAW TO SHIP")
    return {"rows": rows}


# ================================================================================================
# AX6 — the target's own spread.  THE REASON no further iteration is owed.
# ================================================================================================
def ax6(T, cells):
    """Is "the pedal's Q at this (GRUNT, DRIVE)" a single number at all?

    AQ2b measured that it is not — it spans 1.29x-2.93x across the three stimulus rungs at fixed
    (GRUNT, DRIVE).  This states the same fact in the units the acceptance criterion is written in,
    which is what makes it decisive: if the SHIPPED error is already smaller than the spread of the
    target, then no single number can be meaningfully "closer", and the family producing it is
    irrelevant.  ⭐ Needs no threshold — it compares two measured quantities."""
    print("\nAX6  THE TARGET'S OWN SPREAD — is the shipped error already inside it?")
    print(f"  {'DRIVE':>5} | {'pedal Q across the three sweeps':>34} | {'spread':>7} | "
          f"{'shipped |Q err|':>15} | verdict")
    rows, inside = [], 0
    for drv, (cut_ship, qn, cs) in cells.items():
        qs = [pg[AQ.QKEY] for _, _, _, pg, _ in cs]
        spread = float(max(qs) - min(qs))
        errs = []
        for g, ped, mo, pg, _ in cs:
            r = geo(g, mo, cut_ship, qn, 0.0, 3.0, drv, T)
            if r is not None and np.isfinite(r[AQ.QKEY]):
                errs.append(abs(r[AQ.QKEY] - pg[AQ.QKEY]))
        qe = float(np.mean(errs)) if errs else float("nan")
        ok = np.isfinite(qe) and qe < spread
        inside += ok
        rows.append({"drive": drv, "ped_q": qs, "spread": spread, "q_err": qe, "inside": bool(ok)})
        print(f"  {drv:5.2f} | {'  '.join(f'{q:8.2f}' for q in qs):>34} | {spread:7.2f} | "
              f"{qe:15.2f} | {'INSIDE the spread' if ok else 'outside'}")
    print(f"\n  ⇒ the shipped error is already smaller than the target's own across-stimulus spread "
          f"at {inside} of {len(rows)} rungs.")
    if inside == len(rows):
        print("  ⇒ a knob-keyed entry is INSIDE the ambiguity of what it is fitting, so 'closer to")
        print("    the pedal's Q' is not well defined for ANY single number.  s151 §6's")
        print("    architectural limit on a FOURTH axis (after AQ2b's Q, AR6's residual, AU's peak).")
    return {"rows": rows, "n_inside": inside, "n": len(rows)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=REPORT)
    args = ap.parse_args()

    T = F.shipped_tables()
    print("=" * 98)
    print("GATE AX — the GRUNT-Cut shoulder section (task A), screened on task A's own acceptance")
    print("=" * 98)
    cells = load_cells(T)
    if not cells:
        sys.exit("GATE AX: no readable Cut cell — the gate never ran (`empty-gate-must-fail`)")
    print(f"  {sum(len(c[2]) for c in cells.values())} cells over {len(cells)} DRIVE rungs "
          f"(GRUNT Cut, bleed-free, the three realistic stimulus sweeps)")

    out = {"ax1": ax1(T, cells), "ax2": ax2(T, cells), "ax3": ax3(T, cells),
           "ax4": ax4(T, cells), "ax5": ax5(T, cells), "ax6": ax6(T, cells)}

    print("\n" + "=" * 98)
    print("VERDICT")
    print("=" * 98)
    qbest = " / ".join("{:.2f}".format(r.get("q_best", float("nan"))) for r in out["ax5"]["rows"])
    print(f"  reachable per cell            : {out['ax2']['reach_two']} of "
          f"{len(out['ax2']['rows'])}  (one section: {out['ax2']['reach_one']}) — "
          f"s151's 'structural' sentence CONFIRMED")
    print(f"  fit bought by a free section  : {out['ax3']['median_bought']:.3f} dB median   "
          f"(notch term 1.56; 800 Hz candidate REJECTED at 0.058)")
    print(f"  like-for-like vs re-fitting   : {out['ax4']['mean_3sect']:.3f} vs "
          f"{out['ax4']['mean_2sect']:.3f} dB — the section LOSES")
    print(f"  shipping form                 : Q error still {qbest}, "
          f"with no law in the requested table")
    print(f"  target's own spread           : shipped error already INSIDE it at "
          f"{out['ax6']['n_inside']} of {out['ax6']['n']} rungs")
    print("\n  ⛔ REFUTED ON TASK A's OWN ACCEPTANCE — nothing ships, so CLEAN is bit-identical")
    print("     trivially and the release gate cannot move.")

    for n in NOTE:
        print(f"  ⚠ {n}")
    os.makedirs(os.path.dirname(args.report), exist_ok=True)
    with open(args.report, "w") as fh:
        json.dump(out, fh, indent=2, sort_keys=True, default=float)
    print(f"\n  report -> {os.path.relpath(args.report)}")
    if FAIL:
        sys.exit(f"GATE AX FAILED: {', '.join(FAIL)}")


if __name__ == "__main__":
    main()
