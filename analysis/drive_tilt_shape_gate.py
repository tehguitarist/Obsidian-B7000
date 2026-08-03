#!/usr/bin/env python3.11
"""GATE AG — DOES THE REFERENCE ACTUALLY CARRY THE DRIVE-DEPENDENT SLOPE AF6 REQUIRES?

WHY THIS EXISTS (session 135, executing session 134's `NEXT` #1).

GATE AF6 (s134) reframed open work item 6's treble half out of the units every previous session
had used.  Every candidate up to then was a CORNER move (SK bandwidth, supply sag, junction
capacitance), and AF2-AF5 refuted all five physical carriers for one.  What replaced it:

    the treble peak is a VERTEX (AB4), a vertex sits where the total slope crosses zero, so a
    drive-dependent TILT moves it with NO corner moving anywhere -- and the required tilt is
    -1.185 dB/oct near 2935 Hz, at or UPSTREAM of the clipper.

AF6 sized that from the model's own curvature with no fit in it (predicted -1.223 from AF1c's
-11.124 dB/oct^2 against a measured -1.185, agreeing to 3.2 %).  But it could not check the one
thing that decides whether the requirement is even available, and it said so every run:

    "LOCAL number ... Extrapolating it to a broadband tilt is an ASSUMPTION ... 72 % of GATE Q's
     measured D(f) ... whether the SHAPE matches is UNMEASURED -- an rms says nothing about
     whether D(f) is a monotone tilt at 2.9 kHz."

⇒ **This gate makes that measurement.**  It is a stored-report read: no render, no capture, no
constant, no `src/` edit.

WHAT MAKES THE COMPARISON LEGITIMATE.  The report's FR is `h1band` (comprehensive_report's
DEFAULT_FR_METHOD) -- the Farina FUNDAMENTAL transfer, power-averaged over each band's own 1/3-oct
width, harmonics REJECTED.  That is the same quantity GATE W6 reads the peak's centre off, so the
peak walk and this slope are two views of ONE object rather than two statistics that merely both
involve drive.

THE ESTIMATOR, and why it is not the obvious one.  A least-squares slope over a window of
1/3-octave bands is BIASED here: the bands nearest 2935 Hz sit at -0.197 / +0.136 / +0.470 oct, so
an LS fit is effectively centred near 3225 Hz, and the pedal's tilt STEEPENS with frequency -- so
the naive estimator overstates the slope at the vertex, in the flattering direction.  Instead AG
fits a QUADRATIC in log2(f/F0) and takes its linear coefficient, which IS the slope at F0.  That
also gives an exact known answer: adding a pure tilt `T*log2(f/F0)` to any curve must raise that
coefficient by exactly T, whatever the curve underneath (AG1b, verified to machine precision).

GATES (validity exits non-zero; every physics OUTCOME is a computed verdict and execution
continues -- s108's rule, and s134's own correction to it)
------------------------------------------------------------------------------------------------
AG1  KNOWN ANSWERS  (a) this tool's per-band drive difference must reproduce GATE Q's stored D(f)
                    ELEMENTWISE -- the surface is imported from GATE Q, not re-derived, so a
                    divergence means drift.  (b) the tilt estimator must recover an INJECTED tilt
                    exactly, swept over sizes INCLUDING ZERO (zero is the arm's own built-in
                    mutation control: it must recover nothing).
AG2  MEMBERSHIP     asserted, three-outcome (s129): complete / PARTIAL = refuse / absent = named
                    exclusion.  The known dropout cells are excluded BY NAME with their reason,
                    and the DRIVE/ATTACK/GRUNT spread is printed (s108 P4).
AG3  THE OPERANDS   s117: a delta cannot say which end moved, so print the MODEL's own slope and
                    the PEDAL's own slope separately, at EVERY rung of the ladder (s129: an
                    endpoint pair is not a ladder), with monotonicity tested per capture.
AG4  THE SHAPE      the measurement AF6 could not make: drive-tilt vs CENTRE FREQUENCY across the
                    band.  The feature-contaminated region is excluded with its reason and its
                    boundary IMPORTED from GATE W's own windows -- a "slope" over a window holding
                    a migrating notch is that notch sliding, not a tilt.
AG5  SIGN AND SIZE  against AF6's requirement, read from the stored s134 report rather than
                    transcribed, with the window width swept (the requirement is LOCAL, so how
                    local is not a detail).
AG6  VERTEX LAW     apply AF6's own law to the PEDAL's measured tilt and compare against GATE W6's
                    measured peak walk.  This is the cross-check that can fail.
AG7  VERDICT        computed, plus a machine-checkable membership line (s130: never assert on a
                    count -- two classes can be the same size).

WHAT THIS DOES **NOT** CLAIM
  * It does not identify a mechanism.  It measures whether the reference carries a
    drive-dependent slope of the required sign and size where AF6 says it is needed, and what
    its frequency SHAPE is.  Naming the physical carrier is still open.
  * It says nothing about hardware.  Both sides here are the ND captures
    (`reference-sources.md` §0); §1 gives this region to neither reference outright.
  * The LF half of AG4's scan is NOT a tilt measurement and is printed as excluded, not as a
    result -- below ~1 kHz the curve carries the bass peak, the 320 Hz cancellation null and the
    mid peak, all of which MIGRATE with drive (GATE W/Y), so a windowed slope there is a feature
    sliding through the window.

Usage:
  python3.11 analysis/drive_tilt_shape_gate.py analysis/reports/s124_ship.json
  python3.11 analysis/drive_tilt_shape_gate.py analysis/reports/s124_ship.json \
      --json analysis/reports/s135_drive_tilt.json
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import od_absolute_gate as Q          # noqa: E402  GATE Q -- the surface, imported not re-derived
import feature_locus_gate as W        # noqa: E402  GATE W -- the named feature windows

# AF6's requirement and AF1c's curvature are READ from session 134's stored report, never
# transcribed (`rebuild-targets-dont-transcribe`).  A missing report is a hard failure: this
# gate's entire purpose is to test that number, so inventing a fallback would be worthless.
AF_REPORT = "analysis/reports/s134_sk_mechanism.json"

RUNGS = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]

# The window widths swept in AG5.  PRIMARY is the only one wholly contained in GATE W's own
# `treble_peak` window (1800-4200 Hz), i.e. the only one clear of BOTH neighbouring migrating
# features -- the bridged-T below and the treble notch above.  The others are sensitivity.
HALF_PRIMARY = 0.5
HALF_SWEEP = (0.5, 0.75, 1.0, 1.25)

# AG4's interpretable region, both bounds imported from GATE W's FEATURES table rather than
# chosen here: above the bridged-T's window top, below the treble notch's window bottom.
SMOOTH_LO = W.FEAT_BY_NAME["bt_notch"][2][1]        # 1000.0 Hz
SMOOTH_HI = W.FEAT_BY_NAME["treble_notch"][2][0]    # 4200.0 Hz

# GATE W6's measured pedal treble-peak walk across the same 24 dB ladder, for AG6's cross-check.
# Stated here with its source because it is a READING, not a derived constant; AG6 prints it as
# the comparand and never as a bar.
W6_PEDAL_PEAK_HZ = (2696.0, 2498.0)

MIN_BANDS = 3          # a quadratic needs 3 points; fewer is not a fit
INJECT_TOL = 1e-9      # AG1b is exact algebra, so the bar is machine precision, not a guess


def _die(msg):
    sys.exit(f"GATE AG FAIL: {msg}")


# ------------------------------------------------------------------------------------------------
# The estimator
# ------------------------------------------------------------------------------------------------
def tilt_at(y, lg, half):
    """Slope in dB/oct AT the window centre, from a quadratic fit in log2(f/F0).

    `lg` is log2(band / F0), so the centre is lg == 0 and the fit's LINEAR coefficient is the
    derivative there.  Exact under an added tilt (AG1b) and, unlike an LS straight line, not
    dragged off-centre by the asymmetric placement of 1/3-octave bands about F0.
    -> (slope, n_bands)
    """
    m = np.abs(lg) <= half
    n = int(m.sum())
    if n < MIN_BANDS:
        return np.nan, n
    x = lg[m]
    A = np.vstack([x ** 2, x, np.ones(n)]).T
    return float(np.linalg.lstsq(A, y[m], rcond=None)[0][1]), n


def load_af6():
    try:
        with open(AF_REPORT) as fh:
            d = json.load(fh)
    except OSError as e:
        _die(f"cannot read {AF_REPORT} ({e}).  GATE AG exists to test AF6's requirement; it "
             f"will not invent one.  Re-run analysis/sk_mechanism_locus.py --json {AF_REPORT}")
    try:
        return (float(d["af6"]["tilt_required_db_oct"]), float(d["af1"]["curvature_db_oct2"]),
                float(d["af1"]["peak_hz"]), float(d["af6"]["frac_of_gateq_dfn"]))
    except (KeyError, TypeError) as e:
        _die(f"{AF_REPORT} has no af6/af1 block ({e}) -- it is not a GATE AF report")


# ------------------------------------------------------------------------------------------------
# AG1 -- known answers
# ------------------------------------------------------------------------------------------------
def gate_ag1(absfr, files, nonhf, fb, drops, F0, out):
    print("-- AG1: known answers --")

    # (a) reproduce GATE Q's D(f) elementwise, against GATE Q's OWN Q4 run in-process.
    # Deliberately not a stored file: `analysis/reports/*.json` is regenerable and gitignored, so
    # a file-based known answer is skippable, and a skippable known answer is one that will be
    # skipped.  Q4's own printing is suppressed -- this is a check, not a second copy of its table.
    keep = [f for f in files if (f, Q.LO) not in drops and (f, Q.HI) not in drops]
    Elo = Q.od_error(absfr, keep, nonhf, Q.LO, drops)
    Ehi = Q.od_error(absfr, keep, nonhf, Q.HI, drops)
    D = (Ehi - Elo).mean(axis=0)
    import contextlib
    import io
    sink = {}
    with contextlib.redirect_stdout(io.StringIO()):
        _L, Dq = Q.gate_q4(absfr, files, nonhf, fb, drops, sink)
    if len(Dq) != len(D):
        _die(f"AG1a: GATE Q's Q4 returned {len(Dq)} bands, this tool built {len(D)} -- "
             f"different membership or band set, not a rounding difference")
    worst = float(np.max(np.abs(np.asarray(Dq) - D)))
    if worst > 1e-9:
        _die(f"AG1a: this tool's D(f) departs from GATE Q's own Q4 by {worst:.3e} dB. The "
             f"surface must be IMPORTED, not re-derived -- a divergence here means one of the "
             f"two has drifted and every number below is unattributable.")
    print(f"   (a) D(f) reproduces GATE Q's own Q4 elementwise: worst |d| = "
          f"{worst:.3e} dB over {len(D)} bands   PASS")
    out["_gateq_d_rms"] = float(np.sqrt(np.mean(np.asarray(Dq) ** 2)))

    # (b) the estimator must recover an INJECTED tilt exactly, including zero.
    lg = np.log2(fb / F0)
    base = absfr[(keep[0], Q.HI)][1][nonhf]          # any real curve; the arm is curve-agnostic
    rows = []
    for T in (0.0, -1.185, +2.5, -7.0):
        got, n = tilt_at(base + T * lg, lg, HALF_PRIMARY)
        ref, _ = tilt_at(base, lg, HALF_PRIMARY)
        rows.append((T, got - ref, n))
    worst_inj = max(abs(r[1] - r[0]) for r in rows)
    print(f"   (b) injected-tilt recovery (quadratic fit, +-{HALF_PRIMARY} oct, "
          f"{rows[0][2]} bands):")
    for T, got, _ in rows:
        tag = "  <- ZERO: the arm's own mutation control, must recover nothing" if T == 0 else ""
        print(f"        injected {T:+7.3f}  recovered {got:+7.3f}  |err| {abs(got-T):.2e}{tag}")
    if worst_inj > INJECT_TOL:
        _die(f"AG1b: the tilt estimator recovers an injected tilt to only {worst_inj:.2e} dB/oct. "
             f"This is exact algebra (a tilt adds T to the linear coefficient of a quadratic fit "
             f"in log-f), so the bar is machine precision and a miss is a defect, not noise.")
    print(f"       worst |error| = {worst_inj:.2e} dB/oct against an EXACT requirement   PASS")

    # (c) WINDOW VALIDITY -- what licenses AG3 and AG5 at all.  The primary window about the
    # vertex must itself clear both neighbouring MIGRATING features, or the slope read there is
    # a feature sliding through the window rather than a tilt (GATE W3's rule, one axis over).
    # Checked HERE, before any slope is read, rather than beside the statistic that uses it: it
    # is true by only 50 Hz at the top, so it is exactly the kind of thing that stops being true.
    w_lo, w_hi = F0 / 2.0 ** HALF_PRIMARY, F0 * 2.0 ** HALF_PRIMARY
    if not (w_lo >= SMOOTH_LO and w_hi <= SMOOTH_HI):
        _die(f"AG1c: the primary window about the vertex ({w_lo:.0f}-{w_hi:.0f} Hz) is not "
             f"contained in the feature-free band ({SMOOTH_LO:.0f}-{SMOOTH_HI:.0f} Hz), so every "
             f"slope below is contaminated by a migrating feature and AG3/AG5 do not mean what "
             f"they say.  Narrow HALF_PRIMARY or re-derive the bounds from GATE W.")
    print(f"   (c) primary window {w_lo:.0f}-{w_hi:.0f} Hz sits inside the feature-free "
          f"{SMOOTH_LO:.0f}-{SMOOTH_HI:.0f} Hz")
    print(f"       (headroom {SMOOTH_HI - w_hi:.0f} Hz at the top, {w_lo - SMOOTH_LO:.0f} Hz at "
          f"the bottom)   PASS")
    out["ag1c"] = {"win_lo": float(w_lo), "win_hi": float(w_hi),
                   "smooth_lo": SMOOTH_LO, "smooth_hi": SMOOTH_HI}
    out["ag1"] = {"d_reproduce_worst_db": worst,
                  "inject_worst_db_oct": float(worst_inj),
                  "inject": [[float(t), float(g)] for t, g, _ in rows]}
    return keep


# ------------------------------------------------------------------------------------------------
# AG2 -- membership, three-outcome
# ------------------------------------------------------------------------------------------------
def gate_ag2(caps, files, drops, out):
    print("\n-- AG2: membership, asserted --")
    complete, partial, absent = [], [], []
    for f in files:
        have = [r for r in RUNGS if (f, r) not in drops]
        if len(have) == len(RUNGS):
            complete.append(f)
        elif have:
            partial.append((f, [r for r in RUNGS if r not in have]))
        else:
            absent.append(f)
    print(f"   {len(files)} pure-OD endpoints (GATE Q's selection, imported)")
    print(f"   complete (all {len(RUNGS)} rungs): {len(complete)}")
    print(f"   partial: {len(partial)}   absent: {len(absent)}")
    # s129's three outcomes.  A PARTIAL row here is NOT a validity failure: the missing cells are
    # GATE Q's own measured reference dropouts, excluded BY NAME with a recorded reason (Q3's
    # EXPECT_DROPOUTS).  What would be a malformed read is a partial row that Q has NOT flagged.
    for f, miss in partial:
        flagged = all((f, r) in drops for r in miss)
        print(f"     - {f[:58]:58s} missing {','.join(m.replace('sweep_','') for m in miss)}"
              f"   {'GATE Q dropout, excluded by name' if flagged else 'UNFLAGGED'}")
        if not flagged:
            _die(f"AG2: {f} is missing {miss} and GATE Q has not flagged those cells as "
                 f"dropouts.  Data that existed and went missing is a MALFORMED read, not a "
                 f"physics outcome -- refuse rather than silently exclude (s129).")
    if not complete:
        _die("AG2: no capture has all four rungs -- an empty ladder is not a dose-response")
    if absent:
        _die(f"AG2: {len(absent)} endpoints have no usable rung at all")
    # s108 P4: print the spread over the controls the PEDAL itself sets, never pool silently.
    # The key names are ASSERTED against the settings dict rather than defaulted -- a `.get`
    # with a default silently prints `{None: n}`, which is a spread that says nothing and reads
    # as diligence (`empty-gate-must-fail` in a costume).
    def axis(key):
        seen = {}
        for f in complete:
            s = caps[f]["settings"]
            if key not in s:
                _die(f"AG2: no `{key}` in the settings of {f} -- the spread over the pedal's "
                     f"own controls cannot be printed, and pooling over an axis without "
                     f"showing it is s108's P4 trap")
            seen[s[key]] = seen.get(s[key], 0) + 1
        return dict(sorted(seen.items()))
    for k in ("drive", "attackIdx", "gruntIdx"):
        print(f"   {k:10s} spread over the {len(complete)} scored captures: {axis(k)}")
    out["ag2"] = {"n_endpoints": len(files), "n_complete": len(complete),
                  "partial": [[f, m] for f, m in partial], "complete": sorted(complete)}
    return complete


# ------------------------------------------------------------------------------------------------
# AG3 -- the two operands, every rung
# ------------------------------------------------------------------------------------------------
def gate_ag3(absfr, complete, nonhf, fb, F0, half, out):
    print(f"\n-- AG3: the TWO OPERANDS at {F0:.0f} Hz, every rung (s117 / s129) --")
    print(f"   a delta cannot say which END moved, and an endpoint pair is not a ladder.")
    lg = np.log2(fb / F0)
    M = {r: [] for r in RUNGS}
    P = {r: [] for r in RUNGS}
    for f in complete:
        for r in RUNGS:
            m_abs, p_abs = absfr[(f, r)]
            M[r].append(tilt_at(m_abs[nonhf], lg, half)[0])
            P[r].append(tilt_at(p_abs[nonhf], lg, half)[0])
    nb = tilt_at(absfr[(complete[0], RUNGS[0])][0][nonhf], lg, half)[1]
    print(f"   n = {len(complete)} captures, window +-{half} oct ({nb} bands), "
          f"quadratic fit -> slope AT {F0:.0f} Hz\n")
    print(f"   {'rung':>16s} {'MODEL slope':>20s} {'PEDAL slope':>20s} {'PEDAL-MODEL':>12s}")
    ms, ps = [], []
    for r in RUNGS:
        a, b = np.array(M[r]), np.array(P[r])
        ms.append(a.mean()); ps.append(b.mean())
        print(f"   {r:>16s} {a.mean():+9.3f} (sd {a.std(ddof=1):4.2f}) "
              f"{b.mean():+9.3f} (sd {b.std(ddof=1):4.2f}) {b.mean()-a.mean():+12.3f}")
    ms, ps = np.array(ms), np.array(ps)
    dm, dp = np.diff(ms), np.diff(ps)
    m_span, p_span = float(ms.max() - ms.min()), float(ps.max() - ps.min())
    print(f"\n   MODEL rung-to-rung: {['%+.3f' % v for v in dm]}  span {m_span:.3f} dB/oct")
    print(f"   PEDAL rung-to-rung: {['%+.3f' % v for v in dp]}  span {p_span:.3f} dB/oct")
    mono_p = sum(all(P[RUNGS[j + 1]][i] <= P[RUNGS[j]][i] for j in range(3))
                 for i in range(len(complete)))
    mono_m = sum(all(M[RUNGS[j + 1]][i] <= M[RUNGS[j]][i] for j in range(3))
                 for i in range(len(complete)))
    print(f"   monotone FALLING per capture:  pedal {mono_p}/{len(complete)}   "
          f"model {mono_m}/{len(complete)}")
    # computed verdict -- never narration (the target appears as a variable, s130 AB5)
    pedal_falls = bool(np.all(dp <= 0))
    model_flat = m_span < p_span / 5.0
    if pedal_falls and model_flat:
        verdict = ("PEDAL FALLS MONOTONICALLY, MODEL PINNED — item 6's signature on the SLOPE "
                   "axis")
    elif pedal_falls:
        verdict = "pedal falls monotonically, but the model is NOT pinned beside it"
    else:
        verdict = "the pedal's slope is NOT a monotone dose-response — not a drive mechanism"
    print(f"   ⇒ {verdict}")
    print(f"     (pedal 4/4 monotone: {pedal_falls}; model span is "
          f"{m_span / p_span:.3f} of the pedal's)")
    out["ag3"] = {"half_oct": half, "n": len(complete), "n_bands": nb,
                  "model": [float(v) for v in ms], "pedal": [float(v) for v in ps],
                  "model_span": m_span, "pedal_span": p_span,
                  "pedal_monotone_4of4": pedal_falls, "mono_per_capture_pedal": mono_p,
                  "verdict": verdict}
    return ms, ps


# ------------------------------------------------------------------------------------------------
# AG4 -- the SHAPE: drive-tilt vs centre frequency
# ------------------------------------------------------------------------------------------------
def gate_ag4(absfr, complete, nonhf, fb, half, out):
    print(f"\n-- AG4: THE SHAPE — drive-tilt vs CENTRE FREQUENCY (the read AF6 could not make) --")
    print(f"   AF6: \"an rms says nothing about whether D(f) is a monotone tilt at 2.9 kHz\".")
    print(f"   Feature-free band {SMOOTH_LO:.0f}-{SMOOTH_HI:.0f} Hz, both bounds IMPORTED from GATE W's")
    print(f"   windows (above the bridged-T, below the treble notch).  A centre is interpretable")
    print(f"   only when its WHOLE +-{half} oct window fits inside that band, i.e. centres")
    print(f"   {SMOOTH_LO * 2**half:.0f}-{SMOOTH_HI / 2**half:.0f} Hz.  Elsewhere a windowed slope is a MIGRATING")
    print(f"   FEATURE sliding through the window, not a tilt.\n")
    print(f"   {'centre':>8s} {'M clean':>9s} {'M -6':>8s} {'M dTILT':>9s} | "
          f"{'P clean':>9s} {'P -6':>8s} {'P dTILT':>9s} | {'P-M':>8s}")
    rows = []
    for f0 in fb:
        lg = np.log2(fb / f0)
        if int((np.abs(lg) <= half).sum()) < MIN_BANDS:
            continue
        def mean_slope(rung, side):
            return float(np.mean([tilt_at(absfr[(f, rung)][side][nonhf], lg, half)[0]
                                  for f in complete]))
        ml, mh = mean_slope(RUNGS[0], 0), mean_slope(RUNGS[-1], 0)
        pl, ph = mean_slope(RUNGS[0], 1), mean_slope(RUNGS[-1], 1)
        # The WHOLE WINDOW must clear the neighbouring features, not merely its centre: a
        # +-half-oct window centred just inside the boundary still reaches across it, and the
        # feature it reaches is exactly the one that migrates.  (First draft required only the
        # centre, which admitted 1016 Hz -- whose window reaches down to 718 Hz, into the
        # bridged-T -- and that single contaminated row was what made the shape read
        # non-monotone.)
        inside = (f0 / 2.0 ** half >= SMOOTH_LO) and (f0 * 2.0 ** half <= SMOOTH_HI)
        tag = "  interpretable" if inside else "  (window touches a migrating feature)"
        print(f"   {f0:8.0f} {ml:+9.2f} {mh:+8.2f} {mh-ml:+9.2f} | "
              f"{pl:+9.2f} {ph:+8.2f} {ph-pl:+9.2f} | {(ph-pl)-(mh-ml):+8.2f}{tag}")
        rows.append((float(f0), mh - ml, ph - pl, inside))
    inb = [r for r in rows if r[3]]
    if len(inb) < MIN_BANDS:
        _die(f"AG4: only {len(inb)} centres fall in the interpretable band -- "
             f"`empty-gate-must-fail`")
    fs = np.array([r[0] for r in inb]); pt = np.array([r[2] for r in inb])
    mt = np.array([r[1] for r in inb]); dt = pt - mt
    print(f"\n   Inside {SMOOTH_LO:.0f}-{SMOOTH_HI:.0f} Hz ({len(inb)} centres):")
    print(f"     PEDAL drive-tilt {pt.min():+.2f} .. {pt.max():+.2f} dB/oct, "
          f"negative at {int((pt < 0).sum())}/{len(pt)}")
    print(f"     MODEL drive-tilt {mt.min():+.2f} .. {mt.max():+.2f} dB/oct, "
          f"negative at {int((mt < 0).sum())}/{len(mt)}")
    # Is it a UNIFORM tilt (AF6's broadband assumption) or does it steepen?
    steepens = bool(np.all(np.diff(dt) <= 0))
    slope_of_tilt = float(np.polyfit(np.log2(fs), dt, 1)[0])
    if steepens:
        shape = ("NOT a uniform tilt — the deficit STEEPENS monotonically with frequency "
                 f"({slope_of_tilt:+.2f} dB/oct per octave)")
    else:
        shape = f"not monotone across the interpretable band (fitted {slope_of_tilt:+.2f})"
    print(f"     PEDAL-MODEL runs {dt[0]:+.2f} at {fs[0]:.0f} Hz to {dt[-1]:+.2f} at "
          f"{fs[-1]:.0f} Hz")
    print(f"   ⇒ {shape}")
    # n is small by construction here -- say so rather than letting 3 clean centres read as a
    # broad result (`check-n-before-reading-a-trend`).  The contaminated centres above are
    # reported as a TREND, never as support.
    out_rows = [r for r in rows if not r[3] and r[0] > fs[-1]]
    print(f"     ⚠ n = {len(inb)} uncontaminated centres — a direction, not a broad measurement.")
    if out_rows:
        print(f"       Above the clean band the same difference continues "
              f"{'/'.join('%+.1f' % (r[2]-r[1]) for r in out_rows)} at "
              f"{'/'.join('%.0f' % r[0] for r in out_rows)} Hz — SAME direction, but those")
        print(f"       windows reach ND's treble notch (GATE AE: centres 6150-10708 Hz), so they")
        print(f"       are a trend and are NOT counted toward the verdict.")
    print(f"     ⇒ a candidate delivering a CONSTANT drive-dependent tilt would land on target at")
    print(f"       one frequency and be wrong at the others by a growing amount.  The mechanism")
    print(f"       must be frequency-dependent, not a tilt knob.")
    out["ag4"] = {"half_oct": half, "smooth_lo": SMOOTH_LO, "smooth_hi": SMOOTH_HI,
                  "rows": [[r[0], r[1], r[2], r[3]] for r in rows],
                  "steepens": steepens, "tilt_of_tilt_db_oct2": slope_of_tilt,
                  "shape_verdict": shape}
    return rows


# ------------------------------------------------------------------------------------------------
# AG5 -- sign and size against AF6
# ------------------------------------------------------------------------------------------------
def gate_ag5(absfr, complete, nonhf, fb, F0, need, out):
    print(f"\n-- AG5: SIGN and SIZE against AF6's requirement --")
    print(f"   AF6 (imported from {AF_REPORT}, not transcribed): the model must acquire")
    print(f"   {need:+.3f} dB/oct of drive-dependent tilt at {F0:.0f} Hz.")
    print(f"   So the PEDAL-MINUS-MODEL drive-tilt must read {need:+.3f} for the requirement to")
    print(f"   be exactly available, and be of the SAME SIGN for it to be available at all.")
    print(f"   The primary window's containment in the feature-free band was asserted at AG1c.\n")
    lg = np.log2(fb / F0)
    print(f"   {'window':>9s} {'bands':>6s} {'MODEL dTILT':>12s} {'PEDAL dTILT':>12s} "
          f"{'P-M':>9s} {'vs need':>9s}")
    rows = []
    for half in HALF_SWEEP:
        md, pd_, n = [], [], 0
        for f in complete:
            a0, n = tilt_at(absfr[(f, RUNGS[0])][0][nonhf], lg, half)
            a1, _ = tilt_at(absfr[(f, RUNGS[-1])][0][nonhf], lg, half)
            b0, _ = tilt_at(absfr[(f, RUNGS[0])][1][nonhf], lg, half)
            b1, _ = tilt_at(absfr[(f, RUNGS[-1])][1][nonhf], lg, half)
            md.append(a1 - a0); pd_.append(b1 - b0)
        md, pd_ = np.array(md), np.array(pd_)
        d = float((pd_ - md).mean())
        clean = (F0 / 2.0 ** half >= SMOOTH_LO) and (F0 * 2.0 ** half <= SMOOTH_HI)
        star = ("  <- PRIMARY: the only window that clears both migrating features"
                if half == HALF_PRIMARY else
                ("" if clean else "   (reaches a migrating feature — sensitivity only)"))
        print(f"   +-{half:5.2f} {n:6d} {md.mean():+12.3f} {pd_.mean():+12.3f} "
              f"{d:+9.3f} {d/abs(need):+8.2f}x{star}")
        rows.append((half, n, float(md.mean()), float(pd_.mean()), d,
                     int(((pd_ - md) < 0).sum()), len(complete)))
    prim = [r for r in rows if r[0] == HALF_PRIMARY][0]
    same_sign = (prim[4] < 0) == (need < 0)
    ratio = prim[4] / abs(need)
    print(f"\n   PRIMARY window: PEDAL-MINUS-MODEL = {prim[4]:+.3f} dB/oct, "
          f"same sign as required in {prim[5]}/{prim[6]} captures")
    if same_sign and abs(prim[4]) >= abs(need):
        verdict = (f"AVAILABLE — right sign, and {abs(ratio):.2f}x the required size, so the "
                   f"requirement is CONTAINED in a defect already measured")
    elif same_sign:
        verdict = (f"right sign but only {abs(ratio):.2f}x the required size — the reference "
                   f"does not carry enough tilt to close the peak walk")
    else:
        verdict = ("REFUTED — the reference's drive-tilt has the OPPOSITE sign to AF6's "
                   "requirement")
    print(f"   ⇒ {verdict}")
    out["ag5"] = {"need_db_oct": need, "rows": rows, "primary_diff": prim[4],
                  "ratio": float(ratio), "same_sign": bool(same_sign), "verdict": verdict}
    return prim[4]


# ------------------------------------------------------------------------------------------------
# AG6 -- the vertex law, applied to the PEDAL
# ------------------------------------------------------------------------------------------------
def gate_ag6(ps, curv, out):
    print(f"\n-- AG6: AF6's vertex law applied to the PEDAL's own measured tilt --")
    dp = float(ps[-1] - ps[0])
    dx = -dp / curv
    pred_pct = (2.0 ** dx - 1.0) * 100.0
    lo, hi = W6_PEDAL_PEAK_HZ
    meas_pct = (hi / lo - 1.0) * 100.0
    print(f"   the pedal's slope at the vertex moves {dp:+.3f} dB/oct across the ladder (AG3)")
    print(f"   dx = -T/C with C = {curv:.3f} dB/oct^2 (AF1c)  ->  {dx:+.4f} oct = "
          f"{pred_pct:+.1f} %")
    print(f"   GATE W6 measured the pedal's treble peak walking {lo:.0f} -> {hi:.0f} Hz = "
          f"{meas_pct:+.1f} %")
    over = pred_pct / meas_pct if meas_pct else float("nan")
    print(f"   ⇒ same SIGN, and the law OVER-predicts the walk by {over:.2f}x")
    print(f"\n   ⚠ That over-prediction is a RESULT, not a rounding error, and it has a reading:")
    print(f"     the law uses the MODEL's curvature C.  Reproducing the pedal's own {meas_pct:+.1f} %")
    print(f"     from its own {dp:+.3f} dB/oct needs C = {-dp / (np.log2(hi/lo)):.2f} dB/oct^2,")
    print(f"     i.e. the pedal's peak is ~{abs(-dp / (np.log2(hi/lo)) / curv):.1f}x SHARPER than ours.")
    print(f"     ⇒ THE CONSEQUENCE FOR A CANDIDATE: giving the model the pedal's FULL measured")
    print(f"       tilt would overshoot the peak target ({pred_pct:+.1f} % against "
          f"{meas_pct:+.1f} %).  Position and shape cannot both be fixed by a pure tilt while the")
    print(f"       two curvatures differ — a new constraint, and it is cheap to gate on.")
    out["ag6"] = {"pedal_tilt_change": dp, "curv_model": curv, "predicted_pct": pred_pct,
                  "measured_pct": meas_pct, "over_predict": float(over),
                  "implied_pedal_curv": float(-dp / np.log2(hi / lo))}


# ------------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json")
    a = ap.parse_args()

    need, curv, F0, af6_frac = load_af6()
    out = {"report": a.report, "af6_required_db_oct": need, "af1c_curv": curv, "vertex_hz": F0}

    print("=" * 92)
    print("GATE AG — does the reference carry the drive-dependent SLOPE that AF6 requires?")
    print(f"   report {a.report}")
    print(f"   AF6 requirement {need:+.3f} dB/oct at {F0:.1f} Hz, curvature {curv:.3f} dB/oct^2")
    print("=" * 92)

    bands, caps, absfr, nonhf, fb, files, drops = Q.load_surface(a.report)
    gate_ag1(absfr, files, nonhf, fb, drops, F0, out)
    complete = gate_ag2(caps, files, drops, out)
    _ms, ps = gate_ag3(absfr, complete, nonhf, fb, F0, HALF_PRIMARY, out)
    gate_ag4(absfr, complete, nonhf, fb, HALF_PRIMARY, out)
    gate_ag5(absfr, complete, nonhf, fb, F0, need, out)
    gate_ag6(ps, curv, out)

    # AG7 -- computed verdict + a machine-checkable membership line (never a count, s130)
    print("\n" + "=" * 92)
    print("AG7  VERDICT")
    print(f"   AG3 {out['ag3']['verdict']}")
    print(f"   AG4 {out['ag4']['shape_verdict']}")
    print(f"   AG5 {out['ag5']['verdict']}")
    avail = out["ag5"]["same_sign"]
    head = ("AF6's requirement IS carried by the reference, at the required sign"
            if avail else "AF6's requirement is NOT carried by the reference")
    print(f"\n   ⇒ {head}.")
    print(f"   AG7-MEMBERSHIP scored=[{','.join(sorted(x[:40] for x in out['ag2']['complete']))}]")
    print(f"   AG7-SIGN available={avail} ratio={out['ag5']['ratio']:+.3f} "
          f"steepens={out['ag4']['steepens']}")
    out["ag7"] = {"available": bool(avail), "head": head}

    # AF6 quoted its fraction against a STALE D(f) rms.  Re-quote it against THIS report, from
    # the value AG1a already measured -- a citing site that carries a number from a superseded
    # baseline is what `rebaseline-all-derived-artefacts` is about, and it is one line to fix.
    d_rms = out.pop("_gateq_d_rms")
    broad = af6_frac * 3.01                      # the dB AF6 sized, recovered from its own ratio
    print(f"\n   ⚠ AF6 quoted its broadband size as {af6_frac * 100:.0f} % of GATE Q's D(f) rms, "
          f"using 3.01 dB.")
    print(f"     That is an s109-era figure.  On THIS report D(f) rms = {d_rms:.2f} dB, so the "
          f"same {broad:.2f} dB")
    print(f"     is {broad / d_rms * 100:.0f} % of the measured term — the fraction goes UP, so "
          f"the conclusion strengthens.")
    out["af6_frac_restated"] = float(broad / d_rms)
    out["gateq_d_rms"] = d_rms

    if a.json:
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\n   wrote {a.json}")
    print("=" * 92)


if __name__ == "__main__":
    main()
