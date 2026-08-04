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
import sys, os, re, subprocess, math, json, argparse
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

# ⭐⭐ SESSION 146 — THE SESSION-120 `gain-n18` LADDER JOINS AS A SECOND COMPLETE TAKE.
#   s115 could only read n18 at the top two detents (N18_DETENTS above) because that was all
#   that existed; session 120 captured all nine.  Seven of them (0700..1430) were dialled in ONE
#   sitting (2026-08-03 07:04-07:06) where the n12 ladder was assembled across FOUR separate
#   sessions (Jul 22 / Jul 25 / Jul 29 / Aug 2), so the n18 set is the more internally coherent
#   ladder even though neither is authoritative on absolute knob placement.
#
#   ⚠⚠ THE USER'S ACCURACY STATEMENT, SESSION 146, WHICH SUPERSEDES THE s120 NOTE:
#     "0700, 1200, and 1700 are 100% trustworthy, all other positions are best estimations."
#   The s120 carry-forward had listed FIVE positions as "somewhat the most accurate" (adding
#   0930 and 1430).  That is retired -- it was a softer recollection, and this is a direct
#   statement.  The difference is not cosmetic: it removes the only two non-mechanical
#   positions anyone had treated as reliable.
#
#   ⭐⭐ AND IT IS INDEPENDENTLY CORROBORATED, WHICH IS WHY IT IS USED AS A CONSTRAINT.
#   The three trustworthy positions are EXACTLY the three where the pot has a physical
#   reference (both hard stops + the centre detent), and the captures say so without being
#   told: across two capture sessions 12+ days apart the spread is 0.0000 dB at 0700 and
#   0.0000 dB at 1200, against 0.33-1.77 dB everywhere else.  Those files are confirmed
#   INDEPENDENT recordings, not digital copies -- scalar-nulled they read -84..-86 dB, the
#   same floor as detents whose levels DISAGREE by 1.19 dB.  So the user's recollection and
#   the measurement are two separate sources agreeing on the same three positions.
#   (This is GATE S3's mechanical-reference finding, s113, reproduced on MASTER.)
TRUSTED = ("0700", "1200", "1700")

# ⭐ MECHANICAL REFERENCES.  GATE S3 (s113) measured that a re-dialled pot reproduces EXACTLY
#   only where the travel has a physical reference -- the two hard stops and the centre detent --
#   and is worth up to 2.56 dB anywhere else (s116, 4e+06x separation).  That is a property of the
#   POT, known before any level here is read, so the noise floor is split on it rather than on the
#   spread values themselves (`a threshold you guessed is not a guard`; and splitting on the
#   ranking you are about to cut is `self-selecting-scores`).
MECH_REF = ("0700", "1200", "1700")     # full CCW stop, centre detent, full CW stop

# Captures excluded BY NAME, with the evidence.  A defective capture cannot be excluded by any
# predicate over its settings -- what is wrong with it is not in its settings (s105 M2/M3).
# Each entry must MATCH something, or the exclusion is `empty-gate-must-fail` in a costume.
EXCLUDE = {
    ("1545", "n12"): "GATE T (s115): duplicate of the mis-dialled 1700 n12 pair",
    ("1700", "n12"): "GATE T (s115): 4.447 dB low -- knob-corrupted, was the kOutputMakeup anchor",
    ("1700", "a18"): "s146: differs from the current n18 top AT THE SAME HARD STOP by a "
                     "FREQUENCY-DEPENDENT 11.27 dB span; MASTER is a pure gain, so this is "
                     "physically impossible for a genuine master-only difference (GATE O6). "
                     "The contaminated archived session of s112.",
}

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


def pwl3(m, xb1, fb1, xb2, fb2):
    """Three-segment piecewise-linear pot.  Same endpoints as pwl2 (0 at m=0, 1 at m=1).

    Only ever used to ANSWER a question pwl2 cannot -- whether the 2-segment family is
    what limits the fit -- never as a default.  Two extra parameters against 7 points at a
    1.08 dB floor is exactly the place overfitting lives, so its verdict is gated on
    beating the floor, not on beating pwl2's rms (which extra freedom guarantees).
    """
    m = np.asarray(m, dtype=float)
    xb1, xb2 = min(xb1, xb2), max(xb1, xb2)
    fb1, fb2 = min(fb1, fb2), max(fb1, fb2)
    out = np.where(m <= xb1, fb1 * m / max(xb1, 1e-9),
                   np.where(m <= xb2,
                            fb1 + (fb2 - fb1) * (m - xb1) / max(xb2 - xb1, 1e-9),
                            fb2 + (1.0 - fb2) * (m - xb2) / max(1.0 - xb2, 1e-9)))
    return out


def powerlaw(m, p):
    return np.asarray(m, dtype=float) ** p


def _db(v):
    return 20 * np.log10(np.maximum(v, 1e-12))


def shipped_constant(path, name):
    """Read a shipped constant out of the C++ source.

    NOT transcribed: `verify-the-CONSTANT-not-the-prose` (s35) plus
    `rebuild-targets-dont-transcribe` (s33).  A hardcoded copy here would silently
    become a comparison against a value the plugin no longer carries -- which is
    exactly the failure this whole tool exists to have caught in s115.
    """
    pat = re.compile(rf"^\s*(?:static\s+constexpr\s+)?double\s+{re.escape(name)}\s*=\s*"
                     rf"([0-9.eE+-]+)\s*;")
    with open(path) as fh:
        for ln in fh:
            m = pat.match(ln)
            if m:
                return float(m.group(1))
    raise SystemExit(f"** {name} not found in {path} -- the source moved, refusing to guess")


def fit_form(mm, dd, model, x0, nparam, w=None):
    """Least-squares fit of `model` to `dd`.  `w` = per-point WEIGHTS (1/sigma^2).

    The returned rms is always the UNWEIGHTED one, so every form in the table is
    comparable against the same floor whether or not it was fitted with weights.
    """
    if w is None:
        w = np.ones_like(mm)
    w = np.asarray(w, dtype=float)

    def obj(p):
        e = _db(model(mm, *p)) - dd
        return float(np.sqrt(np.sum(w * e ** 2) / np.sum(w)))

    r = minimize(obj, x0, method="Nelder-Mead",
                 options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 40000})
    e = _db(model(mm, *r.x)) - dd
    return np.atleast_1d(r.x), float(np.sqrt(np.mean(e ** 2))), float(np.abs(e).max()), e


# --------------------------------------------------------------------------------------- render
def render_clean_level(master, xb, fb, xb2, fb2, makeup):
    """sweep_clean RMS (dB) of the CLEAN chain at a master setting.

    The capture side is read at FULL SEND level, so the render must be too: `gainSessionDb` is
    cleared on the template (session 41's 12 dB double-count).
    """
    parsed = parse_capture("master-1700_gain-n12_base-clean.wav")   # base-clean knob template
    parsed["master"] = master
    parsed["gainSessionDb"] = 0
    extra = ["--fit", f"masterTaperBreak={xb:.9g}",
             "--fit", f"masterTaperFrac={fb:.9g}",
             "--fit", f"masterTaperBreak2={xb2:.9g}",
             "--fit", f"masterTaperFrac2={fb2:.9g}",
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
    emit("\n(1) LADDER  [ s146: THREE take-sets -- gain-n12, gain-n18 (s120, complete), archived full-send ]")

    sources = (("n12", lambda d: f"{CAPDIR}/master-{d}_gain-n12_base-clean.wav", 0.0),
               ("n18", lambda d: f"{CAPDIR}/master-{d}_gain-n18_base-clean.wav", pad_n18),
               ("full", lambda d: f"{ARCHDIR}/master-{d}_base-clean.wav", -FULLSEND_PAD_DB),
               ("a18", lambda d: f"{ARCHDIR}/master-{d}_gain-n18_base-clean.wav", pad_n18))

    takes, ladder, excluded_hits = {}, {}, []
    for det, k in KNOB.items():
        t = []
        for tag, pathf, adj in sources:
            p = pathf(det)
            if not os.path.exists(p):
                continue
            if (det, tag) in EXCLUDE:
                excluded_hits.append((det, tag))
                continue
            t.append((tag, seg_rms_db(p) + adj))
        takes[k] = t
        if not t:
            fail(f"master-{det}: every take excluded or missing -- no level at this detent")
        ladder[k] = float(np.mean([v for _, v in t]))

    # the named exclusions must actually MATCH, or they are decoration (s105 M2)
    emit("  named exclusions (a defective capture cannot be excluded by a settings predicate):")
    for key, why in EXCLUDE.items():
        hit = key in excluded_hits
        emit(f"    {'HIT ' if hit else 'MISS'} master-{key[0]} [{key[1]}]: {why}")
        if not hit:
            fail(f"exclusion {key} matched nothing -- it is not excluding what it claims to")

    # ⭐⭐ FRAME KNOWN ANSWER, and it must run BEFORE the take-sets are averaged together.
    #    Averaging two capture sessions assumes they share one absolute frame.  The MECHANICAL
    #    references are where the pot has NO freedom, so any disagreement there is a session-level
    #    gain difference, not knob noise -- and it would be booked as taper SHAPE by the fit.
    emit("\n  ⭐ FRAME CHECK at the mechanical references (no knob freedom => must agree exactly):")
    frame_worst = 0.0
    for det in MECH_REF:
        k = KNOB[det]
        vs = {tag: v for tag, v in takes[k]}
        if len(vs) < 2:
            emit(f"    master-{det}: only {list(vs)} -- single take, cannot check")
            continue
        sp = max(vs.values()) - min(vs.values())
        frame_worst = max(frame_worst, sp)
        emit(f"    master-{det}: " + "  ".join(f"{t}={v:+9.3f}" for t, v in vs.items())
             + f"   spread {sp:.4f} dB")
    emit(f"    => worst {frame_worst:.4f} dB.  The take-sets share ONE absolute frame, so the")
    emit(f"       ladder may be averaged across them without a per-session offset.")
    if frame_worst > 0.05:
        fail(f"the take-sets disagree by {frame_worst:.3f} dB where the pot has no freedom -- "
             f"that is a session gain offset and it would be fitted as taper shape")

    top = ladder[1.0]
    emit(f"\n  {'detent':8s} {'knob':>6s} {'dB re full CW':>14s} {'takes':>16s} {'spread':>8s} {'mech':>5s} {'user':>5s}")
    spread_free, spread_mech = [], []
    for det in sorted(KNOB, key=lambda d: KNOB[d]):
        k = KNOB[det]
        vs = [v for _, v in takes[k]]
        sp = (max(vs) - min(vs)) if len(vs) > 1 else float("nan")
        if len(vs) > 1:
            (spread_mech if det in MECH_REF else spread_free).append(sp)
        emit(f"  {det:8s} {k:6.3f} {ladder[k]-top:+14.3f} "
             f"{'+'.join(n for n, _ in takes[k]):>16s} "
             f"{'' if math.isnan(sp) else format(sp, '.3f'):>8s} "
             f"{'STOP' if det in MECH_REF else '':>5s} {'YES' if det in TRUSTED else 'est':>5s}")
    emit("  (mech = the pot has a physical reference here;  trust = the user's s146 statement.")
    emit("   The two columns coincide exactly, from two independent sources -- see TRUSTED.)")
    if set(TRUSTED) != set(MECH_REF):
        fail("TRUSTED and MECH_REF have diverged -- the corroboration this fit leans on is gone")

    ks = sorted(ladder)
    steps = [ladder[ks[i + 1]] - ladder[ks[i]] for i in range(len(ks) - 1)]
    if min(steps) <= 0:
        fail(f"ladder is not monotone (min step {min(steps):+.3f} dB)")
    emit(f"  monotone: min step {min(steps):+.2f} dB, max {max(steps):+.2f} dB")

    # ---- (2) the noise floor ---------------------------------------------------------------
    emit("\n(2) KNOB-REPOSITIONING NOISE FLOOR  [ measured, and SPLIT ON A PHYSICAL PROPERTY ]")
    emit("  Independent takes of one detent differ only by where the knob was put -- so the")
    emit("  spread IS the floor.  GATE S3 (s113) established that a re-dialled pot reproduces")
    emit("  EXACTLY at a hard stop or the centre detent and not elsewhere, so the two")
    emit("  populations are split on that, known in advance of any spread value here.")
    for det in sorted(KNOB, key=lambda d: KNOB[d]):
        k = KNOB[det]
        if len(takes[k]) < 2:
            emit(f"    master-{det}: single take -- no floor reading")
            continue
        emit(f"    master-{det}: " + "  ".join(f"{t}={v:+9.3f}" for t, v in takes[k])
             + f"   spread {max(v for _, v in takes[k]) - min(v for _, v in takes[k]):7.3f} dB"
             + ("   [mechanical reference]" if det in MECH_REF else ""))

    def _rms(a):
        return float(np.sqrt(np.mean(np.array(a) ** 2))) if a else float("nan")

    floor_free, floor_mech = _rms(spread_free), _rms(spread_mech)
    emit(f"\n  FREE positions      : rms {floor_free:.3f} dB, worst {max(spread_free):.3f} dB, "
         f"n={len(spread_free)}   <-- the floor the SHAPE is resolved against")
    emit(f"  MECHANICAL refs     : rms {floor_mech:.3f} dB, worst {max(spread_mech):.3f} dB, "
         f"n={len(spread_mech)}   <-- no freedom, so ~0 by construction")
    if not spread_free:
        fail("no free-position duplicate -- the floor is unmeasured, so no fit can be qualified")
    floor = floor_free
    emit(f"\n  ⚠ s115 QUOTED 0.847 dB, n=4, POOLING THE TWO POPULATIONS.  Its set contained the")
    emit(f"    0700 hard stop reading exactly 0.000, which deflates an rms over free positions.")
    emit(f"    The comparable s115-membership figure is printed as a control in (3).")
    emit(f"  ⇒ NO taper form is resolvable below {floor:.3f} dB.  Forms within ~1.5x are "
         f"indistinguishable.")

    # ---- (2b) the s115 ladder, REBUILT under its own membership rule as a CONTROL -----------
    # Rebuilt from the same take data rather than transcribed, so s115's quotes stay
    # reproducible and any movement is attributable to MEMBERSHIP rather than to a re-read
    # (`rebuild-targets-dont-transcribe`; `aggregate-moved-check-membership-first`).
    emit("\n(2b) CONTROL -- the s115 ladder, under s115's OWN membership rule")
    ladder_s115, spreads_s115 = {}, []
    for det, k in KNOB.items():
        vs = {t: v for t, v in takes[k]}
        t = []
        if det in N18_DETENTS:
            if "n18" in vs:
                t.append(vs["n18"])
        elif "n12" in vs:
            t.append(vs["n12"])
        if "full" in vs:
            t.append(vs["full"])
        ladder_s115[k] = float(np.mean(t)) if t else float("nan")
        if len(t) > 1:
            spreads_s115.append(max(t) - min(t))
    floor_s115 = _rms(spreads_s115)
    emit(f"  s115 floor, its membership, POOLED across both populations: rms {floor_s115:.3f} dB, "
         f"n={len(spreads_s115)}   (s115 logged 0.847)")
    emit(f"  {'knob':>6s} {'s115':>9s} {'s146':>9s} {'move':>8s}")
    top_s115 = ladder_s115[1.0]
    for k in ks:
        emit(f"  {k:6.3f} {ladder_s115[k]-top_s115:+9.3f} {ladder[k]-top:+9.3f} "
             f"{(ladder[k]-top)-(ladder_s115[k]-top_s115):+8.3f}")
    mv = max(abs((ladder[k] - top) - (ladder_s115[k] - top_s115)) for k in ks)
    emit(f"  => worst ladder move {mv:.3f} dB against a free-position floor of {floor:.3f} dB "
         f"({mv/floor:.2f}x)")

    # ---- (3) taper form --------------------------------------------------------------------
    emit("\n(3) TAPER FORM  [ interior points only; m=0 is a divider null, see the header note ]")
    mm = np.array([k for k in ks if 0.0 < k < 1.0])
    dd = np.array([ladder[k] - top for k in mm])

    x_pwl, rms_pwl, worst_pwl, e_pwl = fit_form(mm, dd, pwl2, [0.6, 0.11], 2)
    x_pow, rms_pow, worst_pow, e_pow = fit_form(mm, dd, powerlaw, [2.2], 1)
    e_ship = _db(powerlaw(mm, 1.998)) - dd
    rms_ship = float(np.sqrt(np.mean(e_ship ** 2)))
    # the INCUMBENT, READ FROM THE SOURCE.
    # ⚠⚠ SESSION 146: the shipped form is THREE segments and `masterTaperBreak` is now the
    # FIRST of two breaks.  Evaluating it through pwl2 -- which is what this tool did until the
    # constants changed underneath it -- still runs and still produces plausible numbers, and
    # would compare the ladder against a curve the plugin does not implement.  So the shipped
    # curve gets ONE evaluator, used everywhere below, and the retired s115 pair is kept as an
    # explicitly-labelled HISTORICAL control (its value can never change again).
    SHIP_XB = shipped_constant("src/dsp/FitParams.h", "masterTaperBreak")
    SHIP_FB = shipped_constant("src/dsp/FitParams.h", "masterTaperFrac")
    SHIP_XB2 = shipped_constant("src/dsp/FitParams.h", "masterTaperBreak2")
    SHIP_FB2 = shipped_constant("src/dsp/FitParams.h", "masterTaperFrac2")
    SHIP_MAKEUP = shipped_constant("src/dsp/GainStaging.h", "kOutputMakeupNominal")
    S115_XB, S115_FB = 0.5927, 0.1137          # RETIRED s146 -- historical control only

    def ship_db(x):
        """dB re full CW of the SHIPPED taper.  Scalar or array."""
        a = np.atleast_1d(np.asarray(x, dtype=float))
        v = _db(pwl3(a, SHIP_XB, SHIP_FB, SHIP_XB2, SHIP_FB2)) - _db(
            pwl3(np.array([1.0]), SHIP_XB, SHIP_FB, SHIP_XB2, SHIP_FB2))
        return v if np.ndim(x) else float(v[0])

    def s115_db(x):
        a = np.atleast_1d(np.asarray(x, dtype=float))
        v = _db(pwl2(a, S115_XB, S115_FB)) - _db(pwl2(np.array([1.0]), S115_XB, S115_FB))
        return v if np.ndim(x) else float(v[0])

    emit(f"  shipped constants, read from src/: masterTaperBreak={SHIP_XB:.6g} "
         f"masterTaperFrac={SHIP_FB:.6g}")
    emit(f"                                     masterTaperBreak2={SHIP_XB2:.6g} "
         f"masterTaperFrac2={SHIP_FB2:.6g}  kOutputMakeupNominal={SHIP_MAKEUP:.6g}")
    e_inc = ship_db(mm) - dd
    rms_inc = float(np.sqrt(np.mean(e_inc ** 2)))
    e_s115 = s115_db(mm) - dd
    rms_s115 = float(np.sqrt(np.mean(e_s115 ** 2)))

    emit(f"  {'form':34s} {'params':>20s} {'rms dB':>8s} {'worst':>8s} {'vs floor':>9s}")
    emit(f"  {'3-seg PWL (SHIPPED, s146)':34s} "
         f"{f'xb={SHIP_XB:.4f} fb={SHIP_FB:.4f}':>20s} {rms_inc:8.3f} "
         f"{float(np.abs(e_inc).max()):8.3f} {rms_inc/floor:8.1f}x")
    emit(f"  {'2-seg PWL (retired s146) [control]':34s} "
         f"{f'xb={S115_XB:.4f} fb={S115_FB:.4f}':>20s} {rms_s115:8.3f} "
         f"{float(np.abs(e_s115).max()):8.3f} {rms_s115/floor:8.1f}x")
    emit(f"  {'2-seg PWL (re-fitted, s146)':34s} "
         f"{f'xb={x_pwl[0]:.4f} fb={x_pwl[1]:.4f}':>20s} {rms_pwl:8.3f} {worst_pwl:8.3f} {rms_pwl/floor:8.1f}x")
    emit(f"  {'power law m^p (re-fitted)':34s} {f'p={x_pow[0]:.4f}':>20s} "
         f"{rms_pow:8.3f} {worst_pow:8.3f} {rms_pow/floor:8.1f}x")
    emit(f"  {'power law p=1.998 (retired s115)':34s} {'p=1.9980':>20s} "
         f"{rms_ship:8.3f} {float(np.abs(e_ship).max()):8.3f} {rms_ship/floor:8.1f}x")
    emit("")
    emit("  per-point residual (dB):")
    emit("     m        " + " ".join(f"{v:6.3f}" for v in mm))
    emit("     SHIPPED  " + " ".join(f"{v:+6.2f}" for v in e_inc))
    emit("     s115     " + " ".join(f"{v:+6.2f}" for v in e_s115))
    emit("     re-fit   " + " ".join(f"{v:+6.2f}" for v in e_pwl))
    emit("     p=1.998  " + " ".join(f"{v:+6.2f}" for v in e_ship))

    # ---- (3b) THE CONSTRAINED FIT ----------------------------------------------------------
    # ⭐⭐⭐ The user's s146 statement changes what this fit IS.  Six of the seven interior
    # points are "best estimations" of a knob position, so their ERROR IS IN x, not in y --
    # the LEVEL of every capture is exact (the pure-gain check reads 0.0002 dB), it is the
    # ROTATION that is uncertain.  Least-squares over all seven treats them as seven equally
    # good y-observations, which is the wrong likelihood and lets six estimates outvote the
    # one position that is known.
    #
    # So: the trustworthy points are CONSTRAINTS, not targets.  Of the three, m=0 is the
    # divider null we deliberately do not reproduce and m=1 is the anchor (0 dB by
    # construction on both sides), so exactly ONE enters the fit -- m=0.5 -- and the family
    # is pinned through it, leaving the estimates to choose only the remaining shape.
    emit(f"\n(3b) CONSTRAINED FIT  [ the s146 trust statement, applied as a CONSTRAINT ]")
    trusted_m = sorted(KNOB[d] for d in TRUSTED if 0.0 < KNOB[d] < 1.0)
    emit(f"  trustworthy positions: {', '.join(TRUSTED)}  ->  inside the fit: "
         f"{trusted_m if trusted_m else 'NONE'}")
    emit(f"    (m=0 is the divider null, deliberately not reproduced; m=1 is the anchor, 0 dB")
    emit(f"     by construction -- neither constrains a taper PARAMETER.)")
    if len(trusted_m) != 1:
        fail(f"expected exactly one trustworthy interior point, got {trusted_m} -- the "
             f"constrained fit below is written for one and must be re-derived")
    m_pin = trusted_m[0]
    tgt_db = float(ladder[m_pin] - top)
    tgt = 10 ** (tgt_db / 20)
    emit(f"  PIN: m={m_pin:.3f} must deliver {tgt_db:+.3f} dB re full CW  (ratio {tgt:.6f})")

    def pwl2_pinned_fb(xb):
        """fb such that pwl2(m_pin; xb, fb) == tgt exactly.  None where no valid fb exists."""
        if m_pin <= xb:
            fb = tgt * xb / m_pin
        else:
            u = (m_pin - xb) / (1.0 - xb)
            if abs(1.0 - u) < 1e-12:
                return None
            fb = (tgt - u) / (1.0 - u)
        return fb if 1e-6 < fb < 1.0 else None

    free_m = np.array([k for k in mm if abs(k - m_pin) > 1e-12])
    free_d = np.array([ladder[k] - top for k in free_m])

    def obj_pinned(p):
        fb = pwl2_pinned_fb(float(p[0]))
        if fb is None:
            return 1e6
        e = _db(pwl2(free_m, float(p[0]), fb)) - free_d
        return float(np.sqrt(np.mean(e ** 2)))

    # ⚠ Multi-start over a GRID, not a single seed at the shipped break.  Seeding from
    # SHIP_XB was correct while the shipped form was pwl2; once s146 made SHIP_XB the FIRST
    # of three segments' breaks the seed landed outside this one-parameter family's valid
    # region entirely and the "fit" silently returned its start.  A candidate's own search
    # must not depend on the incumbent's parameterisation (s118's meaning-change trap, in
    # the optimiser rather than in the physics).
    grid = [x for x in np.linspace(0.05, 0.95, 91) if pwl2_pinned_fb(float(x)) is not None]
    if not grid:
        fail("no valid 2-segment taper passes through the trusted point at ANY break -- "
             "the pinned-2 comparison cannot be formed")
        grid = [0.5]
    xb_c = min(grid, key=lambda x: obj_pinned([x]))
    rp = minimize(obj_pinned, [xb_c], method="Nelder-Mead",
                  options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 40000})
    if pwl2_pinned_fb(float(rp.x[0])) is not None and float(rp.fun) <= obj_pinned([xb_c]):
        xb_c = float(rp.x[0])
    fb_c = pwl2_pinned_fb(xb_c)
    e_c_all = _db(pwl2(mm, xb_c, fb_c)) - dd
    rms_c = float(np.sqrt(np.mean(e_c_all ** 2)))
    e_c_free = _db(pwl2(free_m, xb_c, fb_c)) - free_d
    bias_c = float(np.mean(e_c_free))

    # the incumbent, scored the same way
    e_inc_free = ship_db(free_m) - free_d
    pin_err_inc = float(ship_db(m_pin) - tgt_db)
    pin_err_refit = float((_db(pwl2(m_pin, *x_pwl)) - _db(pwl2(1.0, *x_pwl))) - tgt_db)

    emit(f"\n  {'taper':30s} {'xb':>8s} {'fb':>8s} {'err@PIN':>9s} {'rms(est)':>9s} {'bias(est)':>10s}")
    emit(f"  {'SHIPPED (s146, 3-seg)':30s} {SHIP_XB:8.4f} {SHIP_FB:8.4f} {pin_err_inc:+9.3f} "
         f"{float(np.sqrt(np.mean(e_inc_free**2))):9.3f} {float(np.mean(e_inc_free)):+10.3f}")
    emit(f"  {'unconstrained re-fit (s146)':30s} {x_pwl[0]:8.4f} {x_pwl[1]:8.4f} "
         f"{pin_err_refit:+9.3f} "
         f"{float(np.sqrt(np.mean((_db(pwl2(free_m,*x_pwl))-_db(pwl2(1.0,*x_pwl))-free_d)**2))):9.3f} "
         f"{float(np.mean(_db(pwl2(free_m,*x_pwl))-_db(pwl2(1.0,*x_pwl))-free_d)):+10.3f}")
    emit(f"  {'PINNED to the trusted point':30s} {xb_c:8.4f} {fb_c:8.4f} "
         f"{float(e_c_all[list(mm).index(m_pin)]):+9.3f} {float(np.sqrt(np.mean(e_c_free**2))):9.3f} "
         f"{bias_c:+10.3f}")
    emit(f"  (err@PIN is the error at the ONE position we trust; rms/bias(est) are over the")
    emit(f"   six ESTIMATED positions, where a nonzero BIAS -- not a large rms -- is what says")
    emit(f"   the 2-segment family is inadequate, since hand jitter has no preferred sign.)")

    # Does a RICHER family absorb the bias?  This is the one question that separates
    #   (a) the 2-segment family is too crude to hit the pin and the ladder at once, from
    #   (b) the estimated knob positions are systematically LOW (an undershooting hand),
    # which produce identical residuals under pwl2 and different ones under pwl3.
    # ⚠ pwl3 is NOT proposed as a ship candidate -- 3 extra parameters against 6 estimated
    # points at a 1.08 dB floor is textbook overfitting.  It is here only as a DIAGNOSTIC.
    def obj3(p):
        xb1, fb1, xb2 = float(p[0]), float(p[1]), float(p[2])
        if not (1e-6 < xb1 < xb2 < 1.0 and 1e-6 < fb1 < 1.0):
            return 1e6
        # pin: solve fb2 so that pwl3(m_pin) == tgt
        if m_pin <= xb1:
            return 1e6 if abs(fb1 * m_pin / xb1 - tgt) > 1e-9 else 0.0
        if m_pin <= xb2:
            fb2 = fb1 + (tgt - fb1) * (xb2 - xb1) / max(m_pin - xb1, 1e-12)
        else:
            u = (m_pin - xb2) / (1.0 - xb2)
            fb2 = (tgt - u) / (1.0 - u)
        if not (fb1 < fb2 < 1.0):
            return 1e6
        e = _db(pwl3(free_m, xb1, fb1, xb2, fb2)) - free_d
        return float(np.sqrt(np.mean(e ** 2)))

    best3, best3v = None, 1e9
    for x0 in ([0.3, 0.05, 0.7], [0.4, 0.07, 0.75], [0.25, 0.04, 0.6], [0.45, 0.09, 0.8]):
        r3 = minimize(obj3, x0, method="Nelder-Mead",
                      options={"xatol": 1e-12, "fatol": 1e-14, "maxiter": 60000})
        if float(r3.fun) < best3v:
            best3v, best3 = float(r3.fun), r3.x
    xb1, fb1, xb2 = (float(v) for v in best3)
    if m_pin <= xb2:
        fb2 = fb1 + (tgt - fb1) * (xb2 - xb1) / max(m_pin - xb1, 1e-12)
    else:
        u = (m_pin - xb2) / (1.0 - xb2)
        fb2 = (tgt - u) / (1.0 - u)
    e3_free = _db(pwl3(free_m, xb1, fb1, xb2, fb2)) - free_d
    emit(f"  {'PINNED, 3-seg [DIAGNOSTIC ONLY]':30s} {xb1:8.4f} {fb1:8.4f} "
         f"{float(_db(pwl3(np.array([m_pin]), xb1, fb1, xb2, fb2))[0] - _db(pwl3(np.array([1.0]), xb1, fb1, xb2, fb2))[0] - tgt_db):+9.3f} "
         f"{float(np.sqrt(np.mean(e3_free**2))):9.3f} {float(np.mean(e3_free)):+10.3f}")
    emit(f"     (second break xb2={xb2:.4f} fb2={fb2:.4f})")

    emit(f"\n  per-point residual over the ESTIMATED positions (dB; + = model louder than capture):")
    emit(f"     m        " + " ".join(f"{v:6.3f}" for v in free_m))
    emit(f"     SHIPPED  " + " ".join(f"{v:+6.2f}" for v in e_inc_free))
    emit(f"     PINNED-2 " + " ".join(f"{v:+6.2f}" for v in e_c_free))
    emit(f"     PINNED-3 " + " ".join(f"{v:+6.2f}" for v in e3_free))
    bias3 = float(np.mean(e3_free))
    emit(f"\n  BIAS: shipped {float(np.mean(e_inc_free)):+.3f}   pinned-2 {bias_c:+.3f}   "
         f"pinned-3 {bias3:+.3f} dB")
    if abs(bias3) < 0.5 * abs(bias_c):
        emit(f"  => a richer family ABSORBS most of the bias ⇒ reading (a): the 2-segment")
        emit(f"     family is too crude to satisfy the pin and the ladder together.")
    else:
        emit(f"  => a richer family does NOT absorb the bias ({abs(bias3):.2f} vs "
             f"{abs(bias_c):.2f} dB) ⇒ reading (b): the ESTIMATED positions are")
        emit(f"     systematically low, which no taper shape can fix and which is exactly")
        emit(f"     what an undershooting hand on an unmarked knob produces.")
        emit(f"     ⇒ the estimates cannot outvote the pin, and adding segments is overfitting.")

    # ⭐⭐ THE HEADLINE, AND IT NEEDS NO FIT AT ALL.
    # A taper's value at half rotation is the standard way pot tapers are specified, and the
    # trusted point measures it directly.  circuit.md calls VR8 a 100k *A* taper.
    half_ref = tgt * 100.0
    half_ship = float(pwl3(np.array([0.5]), SHIP_XB, SHIP_FB, SHIP_XB2, SHIP_FB2)[0]) * 100.0
    emit(f"\n  ⭐⭐ THE RESULT, FIT-FREE -- the trusted point IS the taper's half-rotation spec:")
    emit(f"     reference (pedal) at half rotation : {half_ref:5.2f} %   ({tgt_db:+.3f} dB)")
    emit(f"     SHIPPED model at half rotation     : {half_ship:5.2f} %   "
         f"({ship_db(0.5):+.3f} dB)")
    emit(f"     => the model is {pin_err_inc:+.2f} dB at MASTER noon, measured at the one")
    emit(f"        position with no knob freedom, from two independent capture sessions.")
    emit(f"     A textbook audio ('A') taper is specified at 10-15% at half rotation.")
    emit(f"     circuit.md calls VR8 a 100k A taper.")
    for nm, v in (("reference", half_ref), ("shipped model", half_ship)):
        where = ("INSIDE" if 10.0 <= v <= 15.0 else ("BELOW" if v < 10.0 else "ABOVE"))
        emit(f"       {nm:14s} {v:5.2f} %  -> {where} the A-taper band")
    emit(f"     Nothing in any objective knew this -- it is the trusted point restated.")

    gain = rms_inc - rms_pwl
    dpred = float(np.max(np.abs((_db(pwl2(mm, xb_c, fb_c)) - _db(pwl2(1.0, xb_c, fb_c)))
                                - ship_db(mm))))
    emit(f"\n  DECISION:")
    emit(f"    unconstrained re-fit vs shipped : rms {rms_pwl:.3f} vs {rms_inc:.3f} dB, "
         f"worst output difference {abs(pin_err_refit-pin_err_inc):.3f} dB")
    emit(f"      => inside the {floor:.3f} dB knob floor.  A pure re-fit changes nothing real.")
    emit(f"    2-seg PINNED vs shipped         : the 2-segment family's best attempt at the")
    emit(f"      pin; worst output difference from the shipped curve {dpred:.3f} dB, and it")
    emit(f"      carries a {bias_c:+.3f} dB one-signed bias the shipped curve does not.")
    # The uncertainty on the PIN is NOT the knob floor -- the knob has no freedom there.
    # It is the recording repeatability, measured independently in s112 and quoted by
    # `reference-sources.md` §0: two captures of one condition, four days apart, agree to
    # 0.010 dB.  The measured spread here (0.000 dB, n=2) is consistent with it and is not
    # used as the bar, because n=2 cannot establish a floor below one.
    PIN_SIGMA_DB = 0.010
    emit(f"    pin uncertainty  : {PIN_SIGMA_DB:.3f} dB (s112 recording repeatability, "
         f"reference-sources.md §0; measured spread here 0.000 dB at n=2)")
    resolved = abs(pin_err_inc) > 10.0 * PIN_SIGMA_DB
    verdict = ("⛔ THE SHIPPED TAPER MISSES THE TRUSTED POINT -- it is off at a position that "
               "carries NO knob uncertainty, so this is a real defect, not knob noise"
               if resolved else
               "✅ THE SHIPPED TAPER SATISFIES THE PIN -- it reproduces the one trusted "
               "interior position to within its own measurement uncertainty")
    emit(f"    => {verdict}")
    emit(f"       (err@PIN {abs(pin_err_inc):.3f} dB = {abs(pin_err_inc)/PIN_SIGMA_DB:.1f}x the "
         f"pin's own uncertainty; the bar is 10x)")

    # ---- the SHIP candidate, at full precision --------------------------------------------
    # A 3-segment PWL is only defensible because THREE independent things hold at once, and
    # only one of them is a fit statistic:
    #   (i)   it is EXACT at the one trusted interior position (a constraint, not a fit);
    #   (ii)  its segment slopes INCREASE monotonically -- a convex, physically-buildable
    #         resistive track, which pwl2-pinned is structurally unable to be below its break;
    #   (iii) it fits the estimated positions BETTER than the incumbent does (0.665 vs 0.960)
    #         despite carrying a constraint the incumbent does not.
    slopes = (fb1 / xb1, (fb2 - fb1) / (xb2 - xb1), (1.0 - fb2) / (1.0 - xb2))
    emit(f"\n  SHIP CANDIDATE, 3-segment PWL, pinned:")
    emit(f"    masterTaperBreak  = {xb1:.6f}    masterTaperFrac  = {fb1:.6f}")
    emit(f"    masterTaperBreak2 = {xb2:.6f}    masterTaperFrac2 = {fb2:.6f}")
    emit(f"    segment slopes (ratio per rotation): {slopes[0]:.4f} -> {slopes[1]:.4f} "
         f"-> {slopes[2]:.4f}")
    emit(f"    half-rotation fraction: {100*float(pwl3(np.array([0.5]), xb1, fb1, xb2, fb2)[0]):.2f} % "
         f"(A-taper spec 10-15%)")
    if not (slopes[0] < slopes[1] < slopes[2]):
        fail(f"the 3-segment candidate is NOT convex (slopes {slopes}) -- a real audio track is; "
             f"a non-convex 'taper' is a sign the extra freedom went into fitting noise")
    if not (0.10 <= float(pwl3(np.array([0.5]), xb1, fb1, xb2, fb2)[0]) <= 0.15):
        fail("the 3-segment candidate is outside the A-taper 10-15% half-rotation band")

    extra3b = ({
        "pin_m": m_pin, "pin_target_db": tgt_db, "pin_sigma_db": PIN_SIGMA_DB,
        "pin_err_shipped_db": pin_err_inc, "pin_err_refit_db": pin_err_refit,
        "pinned2_break": xb_c, "pinned2_frac": fb_c,
        "pinned2_rms_est_db": float(np.sqrt(np.mean(e_c_free ** 2))), "pinned2_bias_est_db": bias_c,
        "pinned3_break": xb1, "pinned3_frac": fb1,
        "pinned3_break2": xb2, "pinned3_frac2": fb2,
        "pinned3_rms_est_db": float(np.sqrt(np.mean(e3_free ** 2))), "pinned3_bias_est_db": bias3,
        "pinned3_slopes": list(slopes),
        "shipped_rms_est_db": float(np.sqrt(np.mean(e_inc_free ** 2))),
        "shipped_bias_est_db": float(np.mean(e_inc_free)),
        "half_rotation_pct_reference": half_ref, "half_rotation_pct_shipped": half_ship,
    })

    # free corroboration nothing in the fit arranged
    half = float(pwl2(0.5, *x_pwl))
    emit(f"\n  [control] the UNCONSTRAINED 2-seg re-fit passes {100*half:.1f}% at half rotation")
    emit(f"     (the shipped 3-seg figure is in the block above; this row is the retired")
    emit(f"      family's, kept so s115's own corroboration stays reproducible).")
    if not (0.05 <= half <= 0.20):
        fail(f"fitted taper is {100*half:.1f}% at half rotation -- not an audio taper; re-examine")

    emit(f"\n  m=0 reference floor: {ladder[0.0]-top:+.2f} dB (divRatio {10**((ladder[0.0]-top)/20):.4f}).")
    emit(f"     DELIBERATELY NOT reproduced -- divRatio(0) stays exactly 0 so MASTER can mute.")
    emit(f"     See the module header for the three grounds.")

    result = {"pad_n12_to_n18": pad_n18,
              "noise_floor_free_db": floor_free, "noise_floor_mech_db": floor_mech,
              "noise_floor_s115_membership_db": floor_s115,
              "ladder_re_full_cw": {str(k): ladder[k] - top for k in ks},
              "ladder_s115_re_full_cw": {str(k): ladder_s115[k] - top_s115 for k in ks},
              "worst_ladder_move_db": mv,
              "taper_form": "pwl2",
              "shipped_masterTaperBreak": SHIP_XB, "shipped_masterTaperFrac": SHIP_FB,
              "shipped_taper_rms_db": rms_inc,
              "refit_masterTaperBreak": float(x_pwl[0]),
              "refit_masterTaperFrac": float(x_pwl[1]),
              "refit_taper_rms_db": rms_pwl, "refit_taper_worst_db": worst_pwl,
              "refit_gain_db": gain, "worst_output_diff_db": dpred,
              "taper_verdict": verdict,
              "retired_powerlaw_rms_db": rms_ship}
    result.update(extra3b)

    # ---- (4) makeup ------------------------------------------------------------------------
    if not args.no_render:
        emit("\n(4) kOutputMakeup  [ MASTER is a pure post-EQ gain => ONE render fixes the scale ]")
        emit("  ⭐ The anchor is master=1.0, where the taper is 1 for EVERY parameter set -- so the makeup")
        emit("     is taper-INDEPENDENT by construction and (3)'s verdict cannot reach it.")
        emit("     The render nevertheless uses the SHIPPED pair, because that is what ships.")
        # ⚠⚠ FRAME. The render is produced with gainSessionDb cleared, i.e. in the FULL-SEND
        # frame. The capture is a gain-n18 file, so it must be lifted by BOTH pads to match:
        #     n18 -> n12 (pad_n18, 6.000)  ->  full send (FULLSEND_PAD_DB, 12.000)
        # Dropping the second one is a silent 12 dB error that lands entirely in the makeup --
        # which is EXACTLY the defect session 41 found and fixed in this same script (its
        # `cap_level()` applied gain_correction_linear for this reason). It is guarded below.
        r10 = render_clean_level(1.0, SHIP_XB, SHIP_FB, SHIP_XB2, SHIP_FB2, 1.0)
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
        emit(f"  => kOutputMakeup = {makeup:.4f}   "
             f"(SHIPPED {SHIP_MAKEUP} -> {20*math.log10(makeup/SHIP_MAKEUP):+.3f} dB)")
        emit("  (calibration §2: the makeup MAY exceed 1.0 -- do NOT pad for headroom.)")
        if abs(20 * math.log10(makeup / SHIP_MAKEUP)) > 0.05:
            fail(f"the makeup re-derives {20*math.log10(makeup/SHIP_MAKEUP):+.3f} dB from the "
                 f"SHIPPED {SHIP_MAKEUP} on the same anchor capture -- that is not a knob "
                 f"question, it is a scale error and it needs its own explanation")

        # ⭐⭐ KNOWN ANSWER: MASTER is a pure gain, so a render at another master must differ
        # from the m=1 render by EXACTLY the taper ratio.  Nothing about a fit can make this
        # true -- it tests that `MasterOut` IMPLEMENTS the pwl2 the ladder was fitted with.
        # This is the check that would catch a MASTER *behaviour* bug as opposed to a taper
        # value that is merely off, so it is run at THREE rotations, one in each PWL segment
        # and one AT the break (where an off-by-one branch would show and a single midpoint
        # probe would not).
        emit(f"\n  ⭐ KNOWN ANSWER (MASTER is a pure gain, and MasterOut must implement the SHIPPED taper):")
        emit(f"     {'m':>7s} {'measured':>10s} {'predicted':>10s} {'error':>9s}")
        worst_ka = 0.0
        for m in (0.25, SHIP_XB, 0.5, SHIP_XB2, 0.85):
            rm = render_clean_level(m, SHIP_XB, SHIP_FB, SHIP_XB2, SHIP_FB2, 1.0)
            pr = float(ship_db(m))
            worst_ka = max(worst_ka, abs(rm - r10 - pr))
            emit(f"     {m:7.4f} {rm-r10:+10.4f} {pr:+10.4f} {abs(rm-r10-pr):9.4f}"
                 + ("   <-- AT a break" if min(abs(m - SHIP_XB), abs(m - SHIP_XB2)) < 1e-9 else ""))
        emit(f"     => worst {worst_ka:.4f} dB")
        if worst_ka > 0.01:
            fail(f"the render does not follow the taper as a pure gain (worst {worst_ka:.4f} dB) "
                 f"-- MasterOut is not implementing the shipped taper")

        # ---- (5) acceptance across the whole travel ----------------------------------------
        emit("\n(5) ACCEPTANCE  [ predicted vs capture at EVERY detent ]")
        emit(f"  ⚠ The comparison that matters is SHIPPED vs RE-FIT.  The retired power law is")
        emit(f"    kept as a labelled control so s115's own quotes stay reproducible; it is NOT")
        emit(f"    the incumbent and beating it proves nothing (s115 already retired it).")
        emit(f"  {'knob':>6s} {'capture':>9s} {'SHIPPED':>9s} {'err':>7s} {'re-fit':>9s} {'err':>7s}"
             f" {'[p=1.998]':>10s} {'err':>7s}")
        errs_ship, errs_refit, errs_pow = [], [], []
        for k in ks:
            if k == 0.0:
                continue
            cap = ladder[k] - top
            ps = float(ship_db(k))
            pn = float(_db(pwl2(k, *x_pwl)) - _db(pwl2(1.0, *x_pwl)))
            po = float(_db(powerlaw(k, 1.998)))
            errs_ship.append(ps - cap)
            errs_refit.append(pn - cap)
            errs_pow.append(po - cap)
            emit(f"  {k:6.3f} {cap:+9.3f} {ps:+9.3f} {ps-cap:+7.2f} {pn:+9.3f} {pn-cap:+7.2f}"
                 f" {po:+10.3f} {po-cap:+7.2f}")
        wsh = max(abs(e) for e in errs_ship)
        wrf = max(abs(e) for e in errs_refit)
        wpo = max(abs(e) for e in errs_pow)
        emit(f"  worst |err|:  SHIPPED {wsh:.2f} dB   re-fit {wrf:.2f} dB   [control p=1.998 {wpo:.2f}]")
        emit(f"  re-fitting buys {wsh-wrf:+.2f} dB of worst-case error against a "
             f"{floor:.2f} dB free-position floor and a {max(spread_free):.2f} dB worst spread.")
        result.update({"kOutputMakeup_rederived": makeup,
                       "worst_err_shipped_db": wsh, "worst_err_refit_db": wrf,
                       "worst_err_powerlaw_control_db": wpo,
                       "masterout_known_answer_worst_db": worst_ka})

        emit("\n  => RECOMMENDATION (computed, not narrated):")
        if resolved:
            emit(f"     SHIP  FitParams.h  masterTaperBreak = {x_pwl[0]:.6g}")
            emit(f"     SHIP  FitParams.h  masterTaperFrac  = {x_pwl[1]:.6g}")
        else:
            emit(f"     CHANGE NOTHING -- the shipped 3-segment taper is correct at the trusted")
            emit(f"     point ({pin_err_inc:+.3f} dB), convex, and sits at {rms_inc/floor:.2f}x the "
                 f"knob floor")
            emit(f"     over the estimated positions ({rms_inc:.3f} dB rms vs a {floor:.3f} dB floor).")
            emit(f"     ⛔ Do NOT chase the remaining residual: below the floor it is the hand that")
            emit(f"     turned the knob, not the model.")
        emit(f"     kOutputMakeup re-derives {makeup:.4f} vs shipped {SHIP_MAKEUP} "
             f"({20*math.log10(makeup/SHIP_MAKEUP):+.3f} dB).")

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
