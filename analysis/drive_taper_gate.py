#!/usr/bin/env python3.11
"""Phase-7 SESSION 16 — §3j-style PRE-REGISTERED GATE on the DRIVE-taper lever.

RUN THIS BEFORE IMPLEMENTING ANY C-TAPER CURVE. Sessions 12 and 14 both built a reshape and only
then discovered its discriminating signature was absent; the standing protocol is to pre-register
the signature and STOP if it fails. Session 16's plan (handover §3u.6) says "replace (1-x)^p with a
proper C-taper" — but that plan rests on an UNTESTED inference, and this gate tests it.

THE UNTESTED INFERENCE. Session 15 argued: jfetGm (a UNIFORM level scale) does not fix noon, so a
NON-uniform level change (the taper SHAPE) is the remaining lever. That argument has a hole. Both
gm and the taper act on noon through exactly ONE channel — the LEVEL into the CD4049 at the noon
knob. If noon H3-H2 barely responds to level, then it does not matter whether the level change is
uniform or not: the taper cannot fix noon either, and reshaping it would be sessions 12/14 again.
The taper being WRONG (which step 1 measured, independently and bleed-free) and the taper being
the FIX for noon are two different claims. Step 1 established the first. This gate tests the second.

PRE-REGISTERED SIGNATURE — all three must hold, or STOP and do not claim the taper closes noon:
  (A) AUTHORITY. Sweeping the noon VR3 resistance across a wide physical range must move noon
      H3-H2 by a material amount (>= 3 dB, against a ~7 dB shortfall). A flat response = no
      authority = the lever cannot reach the deficit, whatever its shape (L-010: compute the
      magnitude of a mechanism before building it).
  (B) DIRECTION. The MEASURED resistance (step 1) must move noon H3-H2 TOWARD the capture's
      -10.6, not away from it. Note the measurement says the real pedal is QUIETER at noon than
      the model (25.7k vs 17.7k = -2.5 dB), while the model is ALREADY SHORT on noon H3-H2 and
      the gm scan shows H3-H2 RISING with level. If those signs hold, the corrected taper moves
      noon the WRONG WAY and (B) FAILS — an outcome this gate is written to be able to report.
  (C) NO REGRESSION. Applying the measured taper at all five knobs must not push the other four
      drive settings further from the capture ramp than the power law does.

Run at TWO points so the verdict is not an artefact of one clipper: the session-15 beta-only
fitted point, and the physically-nominal clipper (clipA0=25, sat 3.15/3.85).

METHOD NOTE. OfflineRender exposes the taper only as the power-law exponent `driveTaperExp`, but
each render is at ONE drive knob, so an exponent chosen PER RENDER lands that render exactly on any
target resistance:  p_eff(x) = ln(R_target/100k) / ln(1-x).  Endpoints (x=0, x=1) are exponent-
independent, which is also why step 1 could anchor on them.

Run:  /opt/homebrew/bin/python3.11 analysis/drive_taper_gate.py
Log:  analysis/fit_logs/step6_drive_taper_gate.log
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import fit_nonlinear as F
from captures import parse_capture, render_args, RENDER_BIN

FS = 48000
LOG = "analysis/fit_logs/step6_drive_taper_gate.log"
RPOT, RFIX, R15 = 100.0e3, 4.3e3, 330.0e3

# Step-1 measured taper (analysis/drive_taper_bleedfree.py, mean of estimators A and B).
MEASURED_R = {"min": 100.0e3, "9:30": 65.27e3, "noon": 25.66e3, "2:30": 6.33e3, "max": 0.0}
KNOB = {"min": 0.0, "9:30": 0.25, "noon": 0.5, "2:30": 0.75, "max": 1.0}
MODEL_P = 2.5

# Two evaluation points (FIT_KEYS order: satPos satNeg ceilPos ceilNeg beta A0 satLo satHi [clipK]).
POINT_BETAONLY = [0.33045, 1.6862, 1.4315, 0.49194, 1.4233, 20.115, 1.4607, 1.7869]
POINT_PHYSICAL = [0.30, 4.0, 1.0, 0.5, 1.8, 25.0, 3.15, 3.85]

AUTHORITY_MIN_DB = 3.0          # (A) threshold, pre-registered
NOON_SWEEP_R = [8e3, 12e3, 17.68e3, 22e3, 25.66e3, 32e3, 45e3]   # spans model 17.68k & measured 25.66k


def model_R(lbl):
    return RPOT * (1.0 - KNOB[lbl]) ** MODEL_P


def p_eff(lbl, R):
    """Exponent that makes (1-x)^p land on R at THIS knob. Endpoints are exponent-free."""
    x = KNOB[lbl]
    if x <= 0.0 or x >= 1.0:
        return MODEL_P
    return math.log(max(R, 1.0) / RPOT) / math.log(1.0 - x)


def stage_gain_db(R):
    return 20 * math.log10(1 + R15 / (RFIX + R))


def render_profile_at(point, lbl, R):
    """Render the fit tone at drive `lbl` with VR3 forced to resistance R; return the profile."""
    extra = []
    held = dict(F.HELD)
    held["driveTaperExp"] = p_eff(lbl, R)
    for k, v in held.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    for k, v in zip(F.FIT_KEYS, point):
        extra += ["--fit", f"{k}={v}"]
    cap = dict(F.DRIVE_CAPS)
    capname = [c for c, l in F.DRIVE_CAPS if l == lbl][0]
    parsed = parse_capture(capname)
    o = f"/tmp/dtg_{lbl.replace(':', '')}.wav"
    subprocess.run([RENDER_BIN, F.SHORT_IN, o, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    r = A.load(o)
    return F._profile(r[int(0.5 * FS):int(1.15 * FS)])


def h3h2(point, lbl, R):
    p = render_profile_at(point, lbl, R)
    return p["H3"] - p["H2"]


def main():
    F.make_short_input()
    targets = F.capture_targets()
    cap = {l: targets[l]["H3"] - targets[l]["H2"] for l in targets}
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 92)
    emit("SESSION-16 §3j GATE — is the DRIVE taper a viable lever for the noon H3-H2 shortfall?")
    emit("=" * 92)
    emit("Pre-registered: (A) noon must respond >= %.1f dB to VR3 resistance; (B) the MEASURED"
         % AUTHORITY_MIN_DB)
    emit("resistance must move noon TOWARD the capture; (C) no regression at the other knobs.")
    emit("")
    emit("Capture H3-H2 ramp (tone_220):  " + "  ".join(f"{l}={cap[l]:+.1f}" for l in cap))
    emit("")
    emit(f"  {'knob':>6} | {'MODEL R':>9} {'gain':>7} | {'MEASURED R':>11} {'gain':>7} | {'level err':>10}")
    for l in ["min", "9:30", "noon", "2:30", "max"]:
        rm, rx = model_R(l), MEASURED_R[l]
        emit(f"  {l:>6} | {rm/1e3:>8.2f}k {stage_gain_db(rm):>6.2f} | {rx/1e3:>10.2f}k "
             f"{stage_gain_db(rx):>6.2f} | {stage_gain_db(rx)-stage_gain_db(rm):>+9.2f} dB")
    emit("")

    verdicts = {}
    for pname, point in [("beta-only fitted", POINT_BETAONLY), ("physical clipper", POINT_PHYSICAL)]:
        emit("-" * 92)
        emit(f"POINT: {pname}   [" + ", ".join(f"{k}={v:g}" for k, v in zip(F.FIT_KEYS, point)) + "]")
        emit("-" * 92)

        # ---- (A) authority + (B) direction, from one noon sweep ----------------------
        emit("(A)+(B)  noon H3-H2 vs VR3 resistance at noon   [capture wants %+.1f]" % cap["noon"])
        emit(f"  {'R noon':>9} {'stage gain':>11} | {'noon H3-H2':>11} | {'err vs capture':>15}")
        vals = []
        for R in NOON_SWEEP_R:
            v = h3h2(point, "noon", R)
            vals.append(v)
            tag = ""
            if abs(R - 17.68e3) < 1e-6 or abs(R - model_R("noon")) < 50:
                tag = "  <- MODEL (1-x)^2.5"
            if abs(R - MEASURED_R["noon"]) < 50:
                tag = "  <- MEASURED (step 1)"
            emit(f"  {R/1e3:>8.2f}k {stage_gain_db(R):>10.2f} | {v:>+10.1f} | "
                 f"{v-cap['noon']:>+14.1f}{tag}")
        authority = max(vals) - min(vals)
        v_model = h3h2(point, "noon", model_R("noon"))
        v_meas = h3h2(point, "noon", MEASURED_R["noon"])
        moved = abs(v_meas - cap["noon"]) < abs(v_model - cap["noon"])
        emit("")
        emit(f"  (A) authority over the swept range : {authority:.1f} dB "
             f"({'PASS' if authority >= AUTHORITY_MIN_DB else 'FAIL'}, need >= {AUTHORITY_MIN_DB})")
        emit(f"  (B) measured taper moves noon      : {v_model:+.1f} -> {v_meas:+.1f} "
             f"(capture {cap['noon']:+.1f})  err {abs(v_model-cap['noon']):.1f} -> "
             f"{abs(v_meas-cap['noon']):.1f} dB  ({'PASS' if moved else 'FAIL'})")

        # ---- (C) whole ramp ----------------------------------------------------------
        emit("")
        emit("(C)  full ramp — power law vs measured taper, all five knobs")
        emit(f"  {'knob':>6} | {'capture':>8} | {'power law':>10} {'err':>7} | "
             f"{'measured':>9} {'err':>7} | {'verdict':>9}")
        e_pl, e_ms = 0.0, 0.0
        for l in ["min", "9:30", "noon", "2:30", "max"]:
            a = h3h2(point, l, model_R(l))
            b = h3h2(point, l, MEASURED_R[l])
            ea, eb = abs(a - cap[l]), abs(b - cap[l])
            e_pl += ea ** 2
            e_ms += eb ** 2
            emit(f"  {l:>6} | {cap[l]:>+7.1f} | {a:>+9.1f} {ea:>6.1f} | {b:>+8.1f} {eb:>6.1f} | "
                 f"{'better' if eb < ea else 'worse':>9}")
        e_pl, e_ms = math.sqrt(e_pl / 5), math.sqrt(e_ms / 5)
        emit(f"  rms ramp error: power law {e_pl:.2f} dB   measured taper {e_ms:.2f} dB   "
             f"({'IMPROVES' if e_ms < e_pl else 'REGRESSES'})")
        verdicts[pname] = dict(authority=authority, aPass=authority >= AUTHORITY_MIN_DB,
                               bPass=moved, rms_pl=e_pl, rms_ms=e_ms)
        emit("")

    # ---- VERDICT ---------------------------------------------------------------------
    emit("=" * 92)
    emit("VERDICT")
    emit("=" * 92)
    allA = all(v["aPass"] for v in verdicts.values())
    allB = all(v["bPass"] for v in verdicts.values())
    allC = all(v["rms_ms"] < v["rms_pl"] for v in verdicts.values())
    for pname, v in verdicts.items():
        emit(f"  {pname:>18}: (A) authority {v['authority']:5.1f} dB {'PASS' if v['aPass'] else 'FAIL'}"
             f"   (B) direction {'PASS' if v['bPass'] else 'FAIL'}"
             f"   (C) ramp rms {v['rms_pl']:.2f} -> {v['rms_ms']:.2f} "
             f"{'PASS' if v['rms_ms'] < v['rms_pl'] else 'FAIL'}")
    emit("")
    if allA and allB and allC:
        emit("  GATE PASSED at both points — the taper IS a viable lever for the noon shortfall.")
        emit("  Proceed to step (2): implement a proper C-taper curve through the measured points.")
    else:
        emit("  ** GATE NOT PASSED. ** The step-1 measurement stands on its own (it is a direct,")
        emit("  bleed-free, self-tested measurement of a circuit quantity, and the shipped power law")
        emit("  is demonstrably wrong), but the claim that reshaping it CLOSES the noon H3-H2 gap is")
        emit("  NOT supported. Do not present a C-taper as the noon fix.")
        if not allB:
            emit("  Specifically (B): the real pedal is QUIETER at noon than the model, while noon")
            emit("  H3-H2 RISES with level and the model is already SHORT there — so the corrected")
            emit("  taper moves noon the WRONG WAY. The noon deficit must come from somewhere else")
            emit("  (next suspect per §3u.6: the clipper INPUT coupling — GRUNT cap bank + R16 —")
            emit("  for drive-dependent behaviour a memoryless VTC cannot produce).")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
