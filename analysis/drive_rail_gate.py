#!/usr/bin/env python3.11
"""Phase-7 SESSION 16 — §3j PRE-REGISTERED GATE on the DRIVE-stage op-amp RAIL CLAMP.

WHY THIS, NOW. Session 16's planned lever (the DRIVE taper shape) was MEASURED (step 1,
`drive_taper_bleedfree.py`) and then GATED (`drive_taper_gate.py`) — and the gate FAILED on
direction: the real pedal is QUIETER at noon than the model, noon H3-H2 RISES with level, and the
model is already SHORT at noon, so correcting the taper moves noon the WRONG WAY. The taper is
genuinely mis-modelled, but it is not the noon fix. That leaves the drive-axis ramp unexplained.

THE OBSERVATION THAT POINTS HERE. The taper gate also measured, for the first time, how much
AUTHORITY level has at noon at all: sweeping VR3 across 8k-45k (an 11 dB level range) moves noon
H3-H2 by only 7.4 dB at the fitted point and **1.2 dB at a physical clipper**. The capture's ramp
spans 24 dB (min -23.2 -> max +1.0) and its min->noon leg alone is +12.6 dB, while the model's is
+2.5 dB. So the drive-axis ramp is NOT reachable by level at all, however that level is delivered.
Something ELSE must change with the DRIVE knob. Sessions 7-15 searched inside the JFET and the
clipper; this is the third nonlinearity on that axis, and it has been switched OFF the whole time.

THE CANDIDATE. `DriveStage.h`'s own header: "IC2_A at max DRIVE is ~x78 and hits its own op-amp
rails BEFORE the clipper — so the output carries a RailClamp." That clamp exists, is wired through
`PedalChain::setFitParams`, and is disabled: `FitParams::railEnabled = false`. Its stated
precondition — "Enable only AFTER kInputRef is set from the bypass capture" — has been MET since
2026-07-22 (`GainStaging.h`: kInputRef 0.87 is marked ANCHORED, user decision). So the gate on it
is stale, and every nonlinear fit from session 7 onward has rendered with a drive-dependent
nonlinearity that the real circuit has and the model does not.

Its signature is exactly the missing one: inert at low drive (x4.2, nowhere near the rail),
engaging progressively as DRIVE raises the stage gain (x16 at noon, x78 at max). That is a
drive-POSITION-dependent effect and NOT a uniform level scale — the class session 15 concluded it
needed and could not find.

PRE-REGISTERED SIGNATURE — must hold, or STOP and do not pursue the rail as the ramp mechanism:
  (L) LIVENESS FIRST (L-009). railEnabled=1 must CHANGE the render. A null result from a switch
      that does nothing is not evidence. Checked before anything else, per revision of the flag.
  (A) RAMP STEEPENING. There must exist a rail voltage at which the model's min->noon H3-H2 leg
      grows materially toward the capture's +12.6 dB (from the rails-off +2.5). >= +4 dB of extra
      slope is the pre-registered bar — a mechanism that cannot move a 10 dB deficit by 4 dB is
      not the mechanism (L-010: compute the authority before building).
  (B) NOT AT THE TOP'S EXPENSE. The same rail must not blow up 2:30/max, which are already
      slightly HIGH at the fitted point. Judged by whole-ramp rms vs the rails-off baseline.
A very high rail (20 V) is included as the OFF control: it must reproduce the rails-off row.

⚠ WHAT THIS GATE DOES NOT DO. It does not fit anything and it does not choose a rail voltage.
railPos/railNeg are degenerate with kInputRef (GainStaging.h: scaling K and the clip ceiling
inversely is bit-identical), so a rail value chosen here would not be a measurement. The gate asks
only whether the MECHANISM has the right shape and enough authority to be worth fitting properly.

Run:  /opt/homebrew/bin/python3.11 analysis/drive_rail_gate.py
Log:  analysis/fit_logs/step6_drive_rail_gate.log
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import fit_nonlinear as F
from captures import parse_capture, render_args, RENDER_BIN

FS = 48000
LOG = "analysis/fit_logs/step6_drive_rail_gate.log"

POINT_BETAONLY = [0.33045, 1.6862, 1.4315, 0.49194, 1.4233, 20.115, 1.4607, 1.7869]
POINT_PHYSICAL = [0.30, 4.0, 1.0, 0.5, 1.8, 25.0, 3.15, 3.85]

# Symmetric rail magnitudes to sweep (volts about VD), plus 20 V as the OFF control.
RAILS = [1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.5, 6.0, 20.0]
LABELS = ["min", "9:30", "noon", "2:30", "max"]
SLOPE_GAIN_MIN = 4.0            # (A) pre-registered bar, dB of extra min->noon slope


def render_ramp(point, rail=None):
    """H3-H2 at all five drive knobs. rail=None -> rails disabled (the current baseline)."""
    out = {}
    for cap, lbl in F.DRIVE_CAPS:
        extra = []
        for k, v in F.HELD.items():
            extra += ["--fit", f"{k}={v:.9g}"]
        for k, v in zip(F.FIT_KEYS, point):
            extra += ["--fit", f"{k}={v}"]
        if rail is None:
            extra += ["--fit", "railEnabled=0"]
        else:
            extra += ["--fit", "railEnabled=1", "--fit", f"railPos={rail:g}",
                      "--fit", f"railNeg={rail:g}"]
        parsed = parse_capture(cap)
        o = f"/tmp/drg_{lbl.replace(':', '')}.wav"
        subprocess.run([RENDER_BIN, F.SHORT_IN, o, "--os", "8"] + render_args(parsed, extra),
                       check=True, capture_output=True)
        r = A.load(o)
        seg = r[int(0.5 * FS):int(1.15 * FS)]
        p = F._profile(seg)
        out[lbl] = p["H3"] - p["H2"]
    return out


def liveness(point):
    """L-009: prove railEnabled=1 actually changes the output before trusting any null result.
    Rendered at MAX drive (where the stage is x78 and the clamp must bite hardest)."""
    cap = [c for c, l in F.DRIVE_CAPS if l == "max"][0]
    outs = []
    for args in (["--fit", "railEnabled=0"],
                 ["--fit", "railEnabled=1", "--fit", "railPos=2", "--fit", "railNeg=2"]):
        extra = []
        for k, v in F.HELD.items():
            extra += ["--fit", f"{k}={v:.9g}"]
        for k, v in zip(F.FIT_KEYS, point):
            extra += ["--fit", f"{k}={v}"]
        extra += args
        o = f"/tmp/drg_live_{len(outs)}.wav"
        subprocess.run([RENDER_BIN, F.SHORT_IN, o, "--os", "8"] + render_args(parse_capture(cap), extra),
                       check=True, capture_output=True)
        outs.append(A.load(o))
    n = min(len(outs[0]), len(outs[1]))
    d = outs[0][:n] - outs[1][:n]
    rms = float(np.sqrt(np.mean(d ** 2)))
    ref = float(np.sqrt(np.mean(outs[0][:n] ** 2)))
    return rms, 20 * math.log10(rms / (ref + 1e-30) + 1e-30)


def main():
    F.make_short_input()
    targets = F.capture_targets()
    cap = {l: targets[l]["H3"] - targets[l]["H2"] for l in targets}
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 96)
    emit("SESSION-16 §3j GATE — DRIVE-stage op-amp RAIL CLAMP as the missing drive-axis mechanism")
    emit("=" * 96)
    emit("Capture H3-H2 ramp:  " + "  ".join(f"{l}={cap[l]:+.1f}" for l in LABELS))
    emit(f"Capture min->noon leg: {cap['noon']-cap['min']:+.1f} dB   "
         f"(the ramp the model cannot make)")
    emit("")

    for pname, point in [("beta-only fitted", POINT_BETAONLY), ("physical clipper", POINT_PHYSICAL)]:
        emit("-" * 96)
        emit(f"POINT: {pname}")
        emit("-" * 96)

        # ---- (L) liveness, FIRST -------------------------------------------------
        rms, rel = liveness(point)
        live = rel > -80.0
        emit(f"(L) LIVENESS (L-009): railEnabled 0 vs 1 at max drive -> diff rms {rms:.3e} "
             f"({rel:+.1f} dB re signal)  {'LIVE' if live else 'DEAD'}")
        if not live:
            emit("    ** The switch does nothing — every result below would be meaningless.")
            emit("    Fix the flag before drawing ANY conclusion (this is exactly L-009).")
            emit("")
            continue

        base = render_ramp(point, None)
        emit("")
        emit(f"  {'rail':>7} | " + " ".join(f"{l:>7}" for l in LABELS)
             + f" | {'min->noon':>10} {'ramp rms':>9}")
        b_slope = base["noon"] - base["min"]
        b_rms = math.sqrt(np.mean([(base[l] - cap[l]) ** 2 for l in LABELS]))
        emit(f"  {'OFF':>7} | " + " ".join(f"{base[l]:>+7.1f}" for l in LABELS)
             + f" | {b_slope:>+10.1f} {b_rms:>9.2f}   <- current baseline")
        best = None
        for rail in RAILS:
            r = render_ramp(point, rail)
            slope = r["noon"] - r["min"]
            rms_r = math.sqrt(np.mean([(r[l] - cap[l]) ** 2 for l in LABELS]))
            tag = "   <- OFF control" if rail >= 20.0 else ""
            emit(f"  {rail:>6.1f}V | " + " ".join(f"{r[l]:>+7.1f}" for l in LABELS)
                 + f" | {slope:>+10.1f} {rms_r:>9.2f}{tag}")
            if rail < 20.0 and (best is None or slope > best[1]):
                best = (rail, slope, rms_r)
        emit("")
        emit(f"  capture target: min->noon {cap['noon']-cap['min']:+.1f} dB, ramp rms 0.00")
        gain = best[1] - b_slope
        emit(f"  (A) best extra min->noon slope: {gain:+.1f} dB at rail {best[0]:g} V "
             f"({'PASS' if gain >= SLOPE_GAIN_MIN else 'FAIL'}, need >= {SLOPE_GAIN_MIN:+.1f})")
        emit(f"  (B) whole-ramp rms at that rail: {b_rms:.2f} -> {best[2]:.2f} "
             f"({'PASS' if best[2] < b_rms else 'FAIL'})")
        emit("")

    emit("=" * 96)
    emit("HOW TO READ THIS")
    emit("=" * 96)
    emit("  PASS => the rail clamp is a real drive-axis mechanism the model is missing, and the")
    emit("  session-17 fit should enable it and fit railPos/railNeg WITH the clipper (they are")
    emit("  degenerate with kInputRef, so they must be fit, never guessed).")
    emit("  FAIL on (A) => the rail cannot reach the ramp either; the drive-axis deficit is then")
    emit("  not a level/limiting phenomenon anywhere in the OD chain, and the next suspect is a")
    emit("  drive-dependent MEMORY effect (clipper input coupling: GRUNT cap bank + R16, whose")
    emit("  time constants a memoryless VTC cannot reproduce) — handover §3u.6's fallback.")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
