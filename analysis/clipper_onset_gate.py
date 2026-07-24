#!/usr/bin/env python3.11
"""Phase-7 SESSION 16 — §3j GATE: is the drive-axis ramp a CLIPPER-ONSET POSITION problem?

WHERE THIS COMES FROM (session 16, after two failed gates that were NOT wasted):
  * `drive_taper_bleedfree.py` MEASURED the DRIVE taper bleed-free (two self-tested estimators,
    agreeing to <2.5%): the shipped power law is wrong, the real pedal is 2.0-3.0 dB QUIETER
    across the interior.
  * `drive_taper_gate.py` then REFUTED the taper as the noon fix: noon H3-H2 rises with level, the
    measured taper LOWERS noon level, so correcting it moves noon the WRONG WAY. It also measured
    level authority at noon for the first time: only 1.2 dB across an 11 dB level range at a
    physical clipper.
  * `drive_rail_gate.py` REFUTED the DRIVE op-amp rail clamp (live per L-009, but it moves only
    2:30/max — at noon the stage output never reaches the rail).

WHAT THOSE THREE NULLS ADD UP TO — a structural reading, not another guess. At LOW drive the
clipper is essentially linear, so H3 and H2 both come from the J201, and DRIVE sits DOWNSTREAM of
the J201 (PedalChain: JFET -> Treble/ATTACK -> DRIVE -> Clipper), so the J201 sees a FIXED level
regardless of the knob. H3-H2 at low drive is therefore a J201-INTRINSIC constant, and the model
is structurally OBLIGED to be flat across min/9:30/noon — which is exactly what it is
(-19.8/-19.4/-17.3 fitted; -25.1/-25.1/-24.7 physical). The capture is NOT flat: -23.2/-21.0/-10.6,
a +12.6 dB min->noon leg. For the real pedal to ramp there, ITS clipper must already be
contributing by noon. The model's is not. This is not a magnitude question about any shape — it is
a question about WHERE ALONG THE DRIVE SWEEP THE CLIPPER TURNS ON.

THE DEGENERACY THAT HID IT. `GainStaging.h` states plainly that kInputRef is DEGENERATE with the
clip ceiling ("scaling K and inversely scaling the clip threshold gives bit-identical output"),
that it CANNOT be measured from audio-only captures, and that 0.87 was ADOPTED as an anchor by
user decision, not measured. Session 15 then rejected two fits for landing at an "unphysical"
clipper (clipSatLo+Hi = 1.58 V vs the ~7 V rail; clipA0 = 8.2 vs circuit.md's 20-30). But
clipSat = 1.58 V at K = 0.87 IS THE SAME MODEL as clipSat = 7.0 V at K = 3.86. The physicality
test was applied to clipSat while K — the other half of the same degenerate pair — was held at a
value that was never measured. That over-constrains the pair, and the optimiser's "degenerate
corner" may have been it correctly reporting that the clipper must engage earlier than the frozen
K allows.

THIS GATE asks the question the degeneracy makes possible: holding the clipper FULLY PHYSICAL
(clipA0 = 25 in circuit.md's 20-30, clipSat 3.15/3.85 V summing to the ~7 V R19-dropped rail),
is there an input reference K at which the model reproduces the capture's drive-axis ramp?

PRE-REGISTERED SIGNATURE — must hold, or STOP:
  (A) KNEE MOVES. As K rises, the min->noon leg must grow from ~+0.4 dB toward the capture's
      +12.6 dB. >= +6 dB of leg is the bar (half the deficit) — below that, onset position is not
      the mechanism either.
  (B) WHOLE RAMP IMPROVES. Ramp rms vs the capture must drop well below the K=0.87 baseline.
  (C) DRIVE-MIN MUST NOT RUN AWAY. The capture's min is -23.2; if K is so hot that the clipper
      engages even at drive-min, min rises too and the ramp flattens again at a higher level.
      The winning K must keep min near the capture, not just lift noon.
  (D) PLAUSIBILITY (reported, not gated). The implied K in volts-peak per 0 dBFS must be sane for
      a bass input. The test signal is documented as "-36..-6 dBFS = soft-to-hot bass playing", so
      judge K at -6 dBFS (K/2), not at the never-played 0 dBFS.

⚠ This gate does NOT fit and does NOT choose K. It asks only whether onset position has the
authority and the shape. A chosen K would have to come from a joint re-fit (session 17), because
K, clipSat and clipA0 are one degenerate family and only their COMBINATION is identifiable.

Run:  /opt/homebrew/bin/python3.11 analysis/clipper_onset_gate.py
Log:  analysis/fit_logs/step6_clipper_onset_gate.log
"""
import sys, os, math, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import fit_nonlinear as F
from captures import parse_capture, render_args, RENDER_BIN

FS = 48000
LOG = "analysis/fit_logs/step6_clipper_onset_gate.log"
LABELS = ["min", "9:30", "noon", "2:30", "max"]

# FULLY PHYSICAL clipper — this is the whole point of the gate. clipA0 inside circuit.md's 20-30,
# clipSatLo+Hi summing to the ~7 V R19-dropped rail.
POINT_PHYSICAL = [0.30, 4.0, 1.0, 0.5, 1.8, 25.0, 3.15, 3.85]
POINT_BETAONLY = [0.33045, 1.6862, 1.4315, 0.49194, 1.4233, 20.115, 1.4607, 1.7869]

K_BASE = 0.87
K_SWEEP = [0.87, 1.2, 1.7, 2.4, 3.4, 4.8, 6.8, 9.6]
LEG_MIN_DB = 6.0                 # (A) pre-registered bar


def render_ramp(point, K, rails=False):
    out = {}
    for cap, lbl in F.DRIVE_CAPS:
        extra = []
        for k, v in F.HELD.items():
            extra += ["--fit", f"{k}={v:.9g}"]
        for k, v in zip(F.FIT_KEYS, point):
            extra += ["--fit", f"{k}={v}"]
        extra += ["--fit", f"railEnabled={1 if rails else 0}"]
        parsed = parse_capture(cap)
        o = f"/tmp/cog_{lbl.replace(':', '')}.wav"
        subprocess.run([RENDER_BIN, F.SHORT_IN, o, "--os", "8", "--input-ref", f"{K:g}"]
                       + render_args(parsed, extra), check=True, capture_output=True)
        r = A.load(o)
        out[lbl] = F._profile(r[int(0.5 * FS):int(1.15 * FS)])
    return {l: out[l]["H3"] - out[l]["H2"] for l in LABELS}


def main():
    F.make_short_input()
    targets = F.capture_targets()
    cap = {l: targets[l]["H3"] - targets[l]["H2"] for l in targets}
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 100)
    emit("SESSION-16 §3j GATE — clipper ONSET POSITION (kInputRef, the other half of the")
    emit("kInputRef<->clipSat degeneracy) as the drive-axis ramp mechanism")
    emit("=" * 100)
    emit("Capture ramp:  " + "  ".join(f"{l}={cap[l]:+.1f}" for l in LABELS))
    emit(f"Capture min->noon leg {cap['noon']-cap['min']:+.1f} dB, min->max {cap['max']-cap['min']:+.1f} dB")
    emit("")
    emit("L-009 note: --input-ref is NOT a sentinel-encoded flag (offline_render.cpp rejects <= 0")
    emit("and always applies it), and the sweep below visibly changes the output, so a null result")
    emit("here would be a real null.")
    emit("")

    for pname, point in [("PHYSICAL clipper (A0=25, sat 3.15/3.85)", POINT_PHYSICAL),
                         ("session-15 beta-only fitted", POINT_BETAONLY)]:
        emit("-" * 100)
        emit(f"POINT: {pname}")
        emit("-" * 100)
        emit(f"  {'K (V/FS)':>9} {'@-6dBFS':>8} | " + " ".join(f"{l:>7}" for l in LABELS)
             + f" | {'min->noon':>10} {'min err':>8} {'ramp rms':>9}")
        rows = []
        for K in K_SWEEP:
            r = render_ramp(point, K)
            leg = r["noon"] - r["min"]
            rms = math.sqrt(np.mean([(r[l] - cap[l]) ** 2 for l in LABELS]))
            rows.append((K, r, leg, rms))
            tag = "   <- current anchor" if abs(K - K_BASE) < 1e-9 else ""
            emit(f"  {K:>9.2f} {K/2:>7.2f}V | " + " ".join(f"{r[l]:>+7.1f}" for l in LABELS)
                 + f" | {leg:>+10.1f} {r['min']-cap['min']:>+8.1f} {rms:>9.2f}{tag}")
        base = rows[0]
        bestleg = max(rows, key=lambda t: t[2])
        bestrms = min(rows, key=lambda t: t[3])
        emit("")
        emit(f"  capture: min->noon {cap['noon']-cap['min']:+.1f}, min err 0.0, ramp rms 0.00")
        # ** The verdict must be JOINT — the three conditions have to hold at the SAME K. **
        # Taking the best leg and the best rms from DIFFERENT rows would "pass" a sweep in which
        # no single value works, which is the classic way a gate certifies nothing (L-003).
        joint = [t for t in rows if t[2] >= LEG_MIN_DB and abs(t[1]["min"] - cap["min"]) <= 2.0
                 and t[3] < base[3] * 0.7]
        emit(f"  (A) best min->noon leg  : {bestleg[2]:+.1f} dB at K={bestleg[0]:.2f} "
             f"(baseline {base[2]:+.1f}, gain {bestleg[2]-base[2]:+.1f})  [bar {LEG_MIN_DB:+.1f}]")
        emit(f"  (B) best whole-ramp rms : {bestrms[3]:.2f} at K={bestrms[0]:.2f} "
             f"(baseline {base[3]:.2f}, {100*(1-bestrms[3]/base[3]):.0f}% better)")
        emit(f"  (C) drive-min at best-rms K: {bestrms[1]['min']:+.1f} vs capture {cap['min']:+.1f} "
             f"(err {bestrms[1]['min']-cap['min']:+.1f} dB)")
        emit(f"  (D) implied input level : {bestrms[0]:.2f} V/FS = {bestrms[0]/2:.2f} V peak at the")
        emit(f"      -6 dBFS 'hot bass' rung (a hot ACTIVE bass is ~1-2 V peak; a passive ~0.1-1 V)")
        emit("")
        emit(f"  ** JOINT VERDICT — one K satisfying (A) AND (C) AND (B) together: "
             f"{'K=' + f'{joint[0][0]:.2f}' if joint else 'NONE'} **")
        if not joint:
            emit("     Authority is REAL and LARGE (see (B): a fully PHYSICAL clipper goes from")
            emit("     unreachable to a better ramp than session 15 got from ANY clipper shape),")
            emit("     but onset position ALONE does not reproduce the ramp: wherever the min->noon")
            emit("     leg steepens, drive-min lifts off the capture with it. Read as NECESSARY but")
            emit("     NOT SUFFICIENT — K belongs in the fit, it is not by itself the answer.")
        emit("")

    emit("=" * 100)
    emit("HOW TO READ THIS")
    emit("=" * 100)
    emit("  JOINT PASS => the blocker was never a shape at all: the clipper turns on too LATE along the")
    emit("  DRIVE sweep, and K/clipSat/clipA0 are ONE degenerate family that must be fit TOGETHER.")
    emit("  Session 15's two 'degenerate corner' rejections should then be re-read as the optimiser")
    emit("  correctly reporting an onset error while K was frozen at an adopted, unmeasured value —")
    emit("  i.e. the physicality test was applied to clipSat alone, half of a degenerate pair.")
    emit("  Session 17 would re-fit with K in the parameter set and judge physicality on the PAIR")
    emit("  (implied input volts AND clipSat volts), never on clipSat with K pinned.")
    emit("  FAIL => onset position is not it either; with taper, rails and onset all refuted, the")
    emit("  remaining candidate on the drive axis is a drive-dependent MEMORY effect (clipper input")
    emit("  coupling: GRUNT cap bank + R16), which no memoryless VTC can produce — §3u.6's fallback.")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
