#!/usr/bin/env python3
"""MASTER taper + kOutputMakeup — REWRITTEN SESSION 115 (Phase 10 C).

WHY IT WAS REWRITTEN
--------------------
The session-17/41 version was unrunnable and, where it did run, wrong:

  * It anchored BOTH constants on `master-1700_gain-n12_base-clean.wav`, which GATE T
    (`analysis/master_anchor_gate.py`) shows is a DUPLICATE of the 1545 capture at a knob position
    that is neither detent — 4.447 dB below a true master-1700.  `kOutputMakeup` inherited that
    error whole, and because every taper point is `lv[m] / lv[1.0]`, so did `masterTaperExp`.
  * Two of its five captures (`master-0700_base-clean.wav`, `master-0930_base-clean.wav`) were
    moved to `analysis/captures/_archive/` in session 112, so it exited rc=2.
  * Its m=0.50 point was `ref-clean.wav`, the file GATE S2 identified as the contaminated member
    of its own twin pair.
  * It fitted a POWER LAW to three points.  On the corrected ladder no power law fits at all:
    the per-point exponent spans 1.74..3.51.

WHAT THIS VERSION DOES
----------------------
(0) Builds the ladder from the SELF-CONSISTENT gain-n12 series (all one send, so the gain
    corrections cancel exactly), promotes the top two detents from their `gain-n18` re-captures
    through a DIRECTLY-measured pad, and uses the archived full-send captures as a genuine SECOND
    TAKE at the four low detents.
(1) MEASURES the knob-repositioning noise floor from those duplicate detents, and refuses to
    resolve any taper form below it.
(2) Fits candidate taper FORMS, not just an exponent, and prints them all.
(3) Derives kOutputMakeup from ONE render, exploiting the fact that MASTER is a pure post-EQ gain
    — with a second render as the known answer that proves it is one.
(4) Acceptance-checks the shipped pair across the WHOLE travel.

⚠ DESIGN DECISION, session 115 — divRatio(0) is kept at EXACTLY 0.
   The reference does not mute at master=0: it floors at -39.0 dB re full CW (divRatio 0.0112).
   That is GATE L7's finding repeating on the second [ENG] divider.  It is NOT reproduced, on
   three grounds: MASTER is an [ENG] stage that is not on our schematic at all; our drawn divider
   (wiper onto VD) genuinely does go to zero, and a real 100k pot's end resistance would put the
   floor near -70 dB, not -39; and a volume control that cannot mute is a usability regression.
   The floor is therefore a deliberate, recorded departure from the captures, not an oversight.

Run:  /opt/homebrew/bin/python3.11 analysis/master_taper_makeup.py
Log:  analysis/fit_logs/step7_master_taper_makeup.log
"""
import sys, os, subprocess, math, json, argparse
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
from scipy.optimize import minimize
import analyze as A
from captures import parse_capture, render_args, RENDER_BIN
import gen_test_signal as G

FS = 48000
ORIG = "analysis/test_signal_48k.wav"
LOG = "analysis/fit_logs/step7_master_taper_makeup.log"
CAPDIR = "analysis/captures"
ARCHDIR = "analysis/captures/_archive"
DRIVE_TAPER = 1.98

# Detent token -> knob value (7 o'clock = 0.0 ... 5 o'clock = 1.0 over ten clock-hours).
KNOB = {"0700": 0.000, "0815": 0.125, "0930": 0.250, "1045": 0.375, "1200": 0.500,
        "1315": 0.625, "1430": 0.750, "1545": 0.875, "1700": 1.000}
N18_DETENTS = ("1545", "1700")          # the two whose gain-n12 captures are the duplicate pair
FULLSEND_PAD_DB = 12.000                 # captures.py _GAIN_SESSION_MEASURED_DB[-12], s114
SEG = "sweep_clean"

_T = G.segment_times()
_fail = []


def fail(msg):
    _fail.append(msg)


# --------------------------------------------------------------------------------------- levels
def _load(p):
    return A.load(p)


def seg_rms_db(path):
    x = _load(path)
    a, b = _T[SEG]
    s = x[int(a * FS):int(b * FS)]
    return 20 * math.log10(float(np.sqrt(np.mean(s.astype(np.float64) ** 2))) + 1e-300)


def seg_bands(path, nb=29):
    x = _load(path)
    a, b = _T[SEG]
    s = x[int(a * FS):int(b * FS)].astype(np.float64)
    f = np.fft.rfftfreq(len(s), 1 / FS)
    X = np.abs(np.fft.rfft(s))
    e = np.geomspace(25, 16300, nb + 1)
    out = []
    for i in range(nb):
        m = (f >= e[i]) & (f < e[i + 1])
        out.append(10 * math.log10(np.mean(X[m] ** 2)) if m.any() else np.nan)
    return np.array(out)


def flat_offset(pa, pb):
    """Level difference and its frequency span.  A pure gain must have span ~0."""
    d = seg_bands(pa) - seg_bands(pb)
    d = d[np.isfinite(d)]
    return float(d.mean()), float(d.max() - d.min())


# --------------------------------------------------------------------------------------- taper
def pwl2(m, xb, fb):
    """Two-segment piecewise-linear pot -- how an audio taper is actually built.

    Fraction fb of full resistance is reached at rotation xb; linear either side.
    Exactly 0 at m=0 and exactly 1 at m=1, both of which the topology requires.
    """
    m = np.asarray(m, dtype=float)
    return np.where(m <= xb, fb * m / max(xb, 1e-9),
                    fb + (1.0 - fb) * (m - xb) / max(1.0 - xb, 1e-9))


def powerlaw(m, p):
    return np.asarray(m, dtype=float) ** p


def _db(v):
    return 20 * np.log10(np.maximum(v, 1e-12))


def fit_form(mm, dd, model, x0, nparam):
    r = minimize(lambda p: float(np.sqrt(np.mean((_db(model(mm, *p)) - dd) ** 2))),
                 x0, method="Nelder-Mead",
                 options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 40000})
    e = _db(model(mm, *r.x)) - dd
    return np.atleast_1d(r.x), float(np.sqrt(np.mean(e ** 2))), float(np.abs(e).max()), e


# --------------------------------------------------------------------------------------- render
def render_clean_level(master, xb, fb, makeup):
    """sweep_clean RMS (dB) of the CLEAN chain at a master setting.

    The capture side is read at FULL SEND level, so the render must be too: `gainSessionDb` is
    cleared on the template (session 41's 12 dB double-count).
    """
    parsed = parse_capture("master-1700_gain-n12_base-clean.wav")   # base-clean knob template
    parsed["master"] = master
    parsed["gainSessionDb"] = 0
    extra = ["--fit", f"masterTaperBreak={xb:.9g}",
             "--fit", f"masterTaperFrac={fb:.9g}",
             "--fit", f"driveTaperExp={DRIVE_TAPER:.6g}"]
    out = f"/tmp/mtm_{int(round(master*1000)):04d}.wav"
    subprocess.run([RENDER_BIN, ORIG, out, "--os", "4", "--output-makeup", f"{makeup:.9g}"]
                   + render_args(parsed, extra), check=True, capture_output=True)
    r, _ = A.align(_load(out), _load(ORIG))
    a, b = _T[SEG]
    s = r[int(a * FS):int(b * FS)]
    return 20 * math.log10(float(np.sqrt(np.mean(s.astype(np.float64) ** 2))) + 1e-300)


# --------------------------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default="analysis/reports/s115_master_recal.json")
    ap.add_argument("--no-render", action="store_true", help="taper only; skip makeup + acceptance")
    args = ap.parse_args()

    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    lines = []

    def emit(s=""):
        print(s)
        lines.append(s)

    emit("=" * 92)
    emit("MASTER taper + kOutputMakeup  --  REWRITTEN session 115 (Phase 10 C)")
    emit("=" * 92)

    # ---- (0) the pads ----------------------------------------------------------------------
    emit("\n(0) PADS  [ the clean path is linear => every pad is a PURE GAIN, so span must be ~0 ]")
    pad_n18, span_n18 = flat_offset(f"{CAPDIR}/ref-clean_gain-n12.wav",
                                    f"{CAPDIR}/ref-clean_gain-n18.wav")
    emit(f"  n12 -> n18 : {pad_n18:.4f} dB  span {span_n18:.4f} dB   "
         f"(derived WITHOUT the contaminated ref-clean.wav -- GATE S2)")
    if abs(pad_n18 - 6.0) > 0.01 or span_n18 > 0.01:
        fail(f"n12->n18 pad {pad_n18:.4f} / span {span_n18:.4f} is not a clean 6.000 dB")
    emit(f"  full -> n12: {FULLSEND_PAD_DB:.4f} dB  (captures.py, session 114)")

    # ---- (1) the ladder --------------------------------------------------------------------
    emit("\n(1) LADDER  [ gain-n12 primary; top two promoted from gain-n18; archived full-send = 2nd take ]")
    takes, ladder = {}, {}
    for det, k in KNOB.items():
        t = []
        if det in N18_DETENTS:
            t.append(("n18", seg_rms_db(f"{CAPDIR}/master-{det}_gain-n18_base-clean.wav") + pad_n18))
        else:
            t.append(("n12", seg_rms_db(f"{CAPDIR}/master-{det}_gain-n12_base-clean.wav")))
        arch = f"{ARCHDIR}/master-{det}_base-clean.wav"
        if os.path.exists(arch):
            t.append(("full", seg_rms_db(arch) - FULLSEND_PAD_DB))
        takes[k] = t
        ladder[k] = float(np.mean([v for _, v in t]))

    top = ladder[1.0]
    emit(f"  {'detent':8s} {'knob':>6s} {'dB re full CW':>14s} {'takes':>7s} {'spread':>8s}")
    spreads = []
    for det in sorted(KNOB, key=lambda d: KNOB[d]):
        k = KNOB[det]
        vs = [v for _, v in takes[k]]
        sp = (max(vs) - min(vs)) if len(vs) > 1 else float("nan")
        if len(vs) > 1:
            spreads.append(sp)
        emit(f"  {det:8s} {k:6.3f} {ladder[k]-top:+14.3f} "
             f"{'+'.join(n for n, _ in takes[k]):>7s} "
             f"{'' if math.isnan(sp) else format(sp, '.3f'):>8s}")

    ks = sorted(ladder)
    steps = [ladder[ks[i + 1]] - ladder[ks[i]] for i in range(len(ks) - 1)]
    if min(steps) <= 0:
        fail(f"ladder is not monotone (min step {min(steps):+.3f} dB)")
    emit(f"  monotone: min step {min(steps):+.2f} dB, max {max(steps):+.2f} dB")

    # ---- (2) the noise floor ---------------------------------------------------------------
    emit("\n(2) KNOB-REPOSITIONING NOISE FLOOR  [ measured, not assumed ]")
    emit("  Two independent takes of one detent differ only by where the knob was put.")
    for det in sorted(KNOB, key=lambda d: KNOB[d]):
        k = KNOB[det]
        if len(takes[k]) < 2:
            continue
        a, b = takes[k]
        _, sp = flat_offset(f"{ARCHDIR}/master-{det}_base-clean.wav",
                            f"{CAPDIR}/master-{det}_gain-n12_base-clean.wav")
        emit(f"    master-{det}: {a[0]} {a[1]:+9.3f} vs {b[0]} {b[1]:+9.3f}  "
             f"=> {a[1]-b[1]:+7.3f} dB   band-span {sp:.4f} dB (pure gain => knob, not tone)")
    floor = float(np.sqrt(np.mean(np.array(spreads) ** 2))) if spreads else float("nan")
    emit(f"  => noise floor: rms {floor:.3f} dB, worst {max(spreads):.3f} dB, n={len(spreads)}")
    if not spreads:
        fail("no duplicate detent -- the noise floor is unmeasured, so no fit can be qualified")
    emit("  ⇒ NO taper form is resolvable below this.  Forms within ~1.5x of it are indistinguishable.")

    # ---- (3) taper form --------------------------------------------------------------------
    emit("\n(3) TAPER FORM  [ interior points only; m=0 is a divider null, see the header note ]")
    mm = np.array([k for k in ks if 0.0 < k < 1.0])
    dd = np.array([ladder[k] - top for k in mm])

    x_pwl, rms_pwl, worst_pwl, e_pwl = fit_form(mm, dd, pwl2, [0.6, 0.11], 2)
    x_pow, rms_pow, worst_pow, e_pow = fit_form(mm, dd, powerlaw, [2.2], 1)
    e_ship = _db(powerlaw(mm, 1.998)) - dd
    rms_ship = float(np.sqrt(np.mean(e_ship ** 2)))

    emit(f"  {'form':34s} {'params':>20s} {'rms dB':>8s} {'worst':>8s} {'vs floor':>9s}")
    emit(f"  {'2-seg piecewise linear (SHIP)':34s} "
         f"{f'xb={x_pwl[0]:.4f} fb={x_pwl[1]:.4f}':>20s} {rms_pwl:8.3f} {worst_pwl:8.3f} {rms_pwl/floor:8.1f}x")
    emit(f"  {'power law m^p (re-fitted)':34s} {f'p={x_pow[0]:.4f}':>20s} "
         f"{rms_pow:8.3f} {worst_pow:8.3f} {rms_pow/floor:8.1f}x")
    emit(f"  {'power law p=1.998 (SHIPPED)':34s} {'p=1.9980':>20s} "
         f"{rms_ship:8.3f} {float(np.abs(e_ship).max()):8.3f} {rms_ship/floor:8.1f}x")
    emit("")
    emit("  per-point residual (dB):")
    emit("     m        " + " ".join(f"{v:6.3f}" for v in mm))
    emit("     2-seg    " + " ".join(f"{v:+6.2f}" for v in e_pwl))
    emit("     p=1.998  " + " ".join(f"{v:+6.2f}" for v in e_ship))

    if rms_pwl > 1.5 * floor:
        fail(f"the selected form sits at {rms_pwl/floor:.1f}x the noise floor -- not a clean fit")
    if rms_ship < 3.0 * floor:
        fail("the SHIPPED power law is not clearly worse than the floor -- the premise for changing it fails")

    # free corroboration nothing in the fit arranged
    half = float(pwl2(0.5, *x_pwl))
    emit(f"\n  ⭐ FREE CHECK: the fitted taper passes {100*half:.1f}% of full resistance at half")
    emit(f"     rotation.  A textbook audio ('A') taper is specified at 10-15%.  circuit.md calls")
    emit(f"     VR8 a 100k A -- and nothing in the objective knew that.")
    if not (0.05 <= half <= 0.20):
        fail(f"fitted taper is {100*half:.1f}% at half rotation -- not an audio taper; re-examine")

    emit(f"\n  m=0 reference floor: {ladder[0.0]-top:+.2f} dB (divRatio {10**((ladder[0.0]-top)/20):.4f}).")
    emit(f"     DELIBERATELY NOT reproduced -- divRatio(0) stays exactly 0 so MASTER can mute.")
    emit(f"     See the module header for the three grounds.")

    result = {"pad_n12_to_n18": pad_n18, "noise_floor_db": floor,
              "ladder_re_full_cw": {str(k): ladder[k] - top for k in ks},
              "taper_form": "pwl2", "masterTaperBreak": float(x_pwl[0]),
              "masterTaperFrac": float(x_pwl[1]),
              "taper_rms_db": rms_pwl, "taper_worst_db": worst_pwl,
              "shipped_powerlaw_rms_db": rms_ship}

    # ---- (4) makeup ------------------------------------------------------------------------
    if not args.no_render:
        emit("\n(4) kOutputMakeup  [ MASTER is a pure post-EQ gain => ONE render fixes the scale ]")
        # ⚠⚠ FRAME. The render is produced with gainSessionDb cleared, i.e. in the FULL-SEND
        # frame. The capture is a gain-n18 file, so it must be lifted by BOTH pads to match:
        #     n18 -> n12 (pad_n18, 6.000)  ->  full send (FULLSEND_PAD_DB, 12.000)
        # Dropping the second one is a silent 12 dB error that lands entirely in the makeup --
        # which is EXACTLY the defect session 41 found and fixed in this same script (its
        # `cap_level()` applied gain_correction_linear for this reason). It is guarded below.
        r10 = render_clean_level(1.0, x_pwl[0], x_pwl[1], 1.0)
        cap_top_abs = (seg_rms_db(f"{CAPDIR}/master-1700_gain-n18_base-clean.wav")
                       + pad_n18 + FULLSEND_PAD_DB)
        makeup = 10 ** ((cap_top_abs - r10) / 20)

        # KNOWN ANSWER that pins the frame: the SHIPPED makeup was fitted to the corrupted
        # capture, so rendering at 2.599 must reproduce THAT file's level (session 106 read the
        # same agreement as +0.007 dB). If the frame is wrong by a pad, this fails by 12 dB.
        bad_abs = seg_rms_db(f"{CAPDIR}/master-1700_gain-n12_base-clean.wav") + FULLSEND_PAD_DB
        r_ship = r10 + 20 * math.log10(2.599)
        emit(f"  [frame check] render @ shipped makeup 2.599 : {r_ship:+8.3f} dBFS")
        emit(f"  [frame check] the CORRUPTED anchor capture  : {bad_abs:+8.3f} dBFS   "
             f"=> {r_ship-bad_abs:+.3f} dB")
        emit("     (must be ~0: the shipped makeup was fitted to that file. Reproduces s106's +0.007.)")
        if abs(r_ship - bad_abs) > 0.10:
            fail(f"frame check failed by {r_ship-bad_abs:+.3f} dB -- a pad is missing on one side")

        emit(f"  capture, TRUE master-1700 : {cap_top_abs:+8.3f} dBFS")
        emit(f"  render,  makeup=1         : {r10:+8.3f} dBFS")
        emit(f"  => kOutputMakeup = {makeup:.4f}   (shipped 2.599 -> {20*math.log10(makeup/2.599):+.2f} dB)")
        emit("  (calibration §2: the makeup MAY exceed 1.0 -- do NOT pad for headroom.)")

        # KNOWN ANSWER: MASTER is a pure gain, so a render at another master must differ from the
        # m=1 render by EXACTLY the taper ratio.  Nothing about the fit can make this true.
        r05 = render_clean_level(0.5, x_pwl[0], x_pwl[1], 1.0)
        pred = _db(pwl2(0.5, *x_pwl)) - _db(pwl2(1.0, *x_pwl))
        emit(f"\n  ⭐ KNOWN ANSWER (MASTER is a pure gain): render(0.5) - render(1.0)")
        emit(f"     measured {r05-r10:+8.4f} dB   predicted {float(pred):+8.4f} dB   "
             f"error {abs(r05-r10-float(pred)):.4f} dB")
        if abs(r05 - r10 - float(pred)) > 0.01:
            fail("the render does not follow the taper as a pure gain -- MasterOut is not what we think")

        # ---- (5) acceptance across the whole travel ----------------------------------------
        emit("\n(5) ACCEPTANCE  [ predicted vs capture at EVERY detent, both taper forms ]")
        emit(f"  {'knob':>6s} {'capture':>9s} {'NEW pwl2':>9s} {'err':>7s} {'OLD p=1.998':>12s} {'err':>7s}")
        errs_new, errs_old = [], []
        for k in ks:
            if k == 0.0:
                continue
            cap = ladder[k] - top
            pn = float(_db(pwl2(k, *x_pwl)) - _db(pwl2(1.0, *x_pwl)))
            po = float(_db(powerlaw(k, 1.998)))
            errs_new.append(pn - cap)
            errs_old.append(po - cap)
            emit(f"  {k:6.3f} {cap:+9.3f} {pn:+9.3f} {pn-cap:+7.2f} {po:+12.3f} {po-cap:+7.2f}")
        wn, wo = max(abs(e) for e in errs_new), max(abs(e) for e in errs_old)
        emit(f"  worst |err|:  NEW {wn:.2f} dB   OLD {wo:.2f} dB   "
             f"({'IMPROVED' if wn < wo else 'NOT IMPROVED'})")
        if wn >= wo:
            fail("the new taper is not better than the shipped one on whole-travel error")
        result.update({"kOutputMakeup": makeup, "worst_err_new_db": wn, "worst_err_old_db": wo})

        emit("\n  => SHIP:")
        emit(f"     FitParams.h  masterTaperBreak = {x_pwl[0]:.6g}")
        emit(f"     FitParams.h  masterTaperFrac  = {x_pwl[1]:.6g}")
        emit(f"     GainStaging.h kOutputMakeupNominal : 2.599 -> {makeup:.4f}")

    emit("\n" + "=" * 92)
    if _fail:
        emit(f"FAILURES ({len(_fail)}):")
        for f in _fail:
            emit("  ** " + f)
    else:
        emit("OK -- all checks pass")
    emit("=" * 92)

    with open(LOG, "w") as fh:
        fh.write("\n".join(lines) + "\n")
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    result["failures"] = _fail
    with open(args.json, "w") as fh:
        json.dump(result, fh, indent=2)
    print(f"\nlog  {LOG}\njson {args.json}")
    return 1 if _fail else 0


if __name__ == "__main__":
    sys.exit(main())
