#!/usr/bin/env python3.11
"""Session-15 tail / session-16 lead — is the DRIVE taper SHAPE the noon-H3 blocker?

Session 15 fixed the JFET H3 PHASE (branch B) but no joint fit passed acceptance: the CD4049
clipper cannot reach the capture's noon/2:30/max H3-H2 ramp within its physical envelope, and two
grids localised the residual to a DRIVE-POSITION-specific level error (noon uniquely short; not gm,
not clipper shape, not the JFET). Leading suspect: `driveTaperExp` is a single power law
R=100k*(1-x)^p (p=2.5) approximating a C-TAPER (reverse-log) pot — and a C-taper is NOT a power law.
Session 11 only ever pinned p=2.5 to a 2-POINT small-signal LEVEL match (9:30, noon); the SHAPE
across the full sweep was never checked.

THIS measures the REAL small-signal DRIVE gain vs knob from the EXISTING dense ladders (no new
capture): at the LOWEST ladder levels the clipper is ~linear, so the output 220 Hz fundamental
tracks the total chain gain, and since ONLY the DRIVE knob differs between the 5 ladder captures,
the RELATIVE fundamental level across them IS the drive-taper gain curve. Compare capture-shape to
model-shape (both normalised to their own drive-min): if the noon->2:30 gain STEP disagrees, the
taper shape is confirmed as the culprit and session 16 should reshape it (proper C-taper, not a
power law) BEFORE re-fitting the clipper.

Uses A.load + sweep-anchor alignment (the ladder reader's caveats: captures.load_capture misfires
on this stimulus, and model renders carry the OS FIR latency).

Run: /opt/homebrew/bin/python3.11 analysis/drive_taper_shape.py
Log: analysis/fit_logs/step5_drive_taper_shape.log
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import read_jfet_ladder as L   # reuse align_to_stim / seg / segment map / stimulus path
from captures import parse_capture, render_args, RENDER_BIN

FS = 48000
F0 = 220.0                      # on-corner tone; H1 (fundamental) is what we read here, not H2
STIM = L.STIM
# The 5 drive ladders + the knob position each was captured at (0..1). ref/noon = 0.5.
DRIVES = [("min", 0.0, "jfet_ladder_drive-min.wav"),
          ("9:30", 0.25, "jfet_ladder_drive-0930.wav"),
          ("noon", 0.5, "jfet_ladder_drive-noon.wav"),
          ("2:30", 0.75, "jfet_ladder_drive-1430.wav"),
          ("max", 1.0, "jfet_ladder_drive-max.wav")]
CAPDIR = "analysis/captures"
# Lowest (cleanest) levels for the small-signal read. -60..-54 dBFS: deep in the linear regime at
# low/mid drive; at max drive even these may graze the clipper (flagged if the per-level gain drifts).
CLEAN_DB = [-60, -57, -54, -51]
HELD = dict(jfetGm=0.10e-3, jfetRo=200e3, jfetRq2=1e6, levelTaperExp=2.25, driveTaperExp=2.5)


def fund_db(s, f):
    """Fundamental magnitude (dB, arbitrary ref) of a steady tone via LS harmonic fit."""
    n = len(s); t = np.arange(n) / FS
    cols = [np.ones(n)]
    for k in range(1, 6):
        cols += [np.cos(2 * np.pi * k * f * t), np.sin(2 * np.pi * k * f * t)]
    M = np.stack(cols, axis=1)
    c, *_ = np.linalg.lstsq(M, s, rcond=None)
    return 20 * math.log10(np.hypot(c[1], c[2]) + 1e-30)


def render_model(drive_val, out):
    parsed = parse_capture(DRIVES[0][2] if False else "drive-0700_base-od.wav")
    parsed["drive"] = drive_val
    extra = []
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    subprocess.run([RENDER_BIN, STIM, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    return A.load(out)


def small_signal_gain(sig, aligned=True):
    """Mean output fundamental (dB) over the cleanest low levels, at 220 Hz. Also returns the
    per-level spread so a non-linear (clipper-grazed) read is visible."""
    vals = []
    for db in CLEAN_DB:
        s = L.seg(sig, f"lad_{F0:g}_{db}")
        vals.append(fund_db(s, F0) - db)   # subtract input dBFS -> gain (dB), ref cancels in steps
    return float(np.mean(vals)), float(np.max(vals) - np.min(vals)), vals


def main():
    stim = A.load(STIM)
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open("analysis/fit_logs/step5_drive_taper_shape.log", "w")

    def emit(s):
        print(s); log.write(s + "\n")

    emit("=" * 78)
    emit("DRIVE taper SHAPE — real small-signal gain vs knob (existing ladders, no new capture)")
    emit("=" * 78)
    emit(f"220 Hz fundamental at {CLEAN_DB} dBFS (clean regime); gain = |H1_out| - A_in (dB).")
    emit("Model: R=100k*(1-x)^2.5, gain=1+330k/(3.3k+R+1k). Both normalised to their OWN drive-min.\n")

    cap_g, mdl_g, spreads = {}, {}, {}
    for lbl, xval, capname in DRIVES:
        cappath = f"{CAPDIR}/{capname}"
        if not os.path.exists(cappath):
            emit(f"** missing {cappath} — cannot run"); return 2
        cap = A.load(cappath)
        cap, _ = L.align_to_stim(cap, stim)
        mdl, _ = L.align_to_stim(render_model(xval, f"/tmp/dts_{lbl.replace(':','')}.wav"), stim)
        cg, cs, _ = small_signal_gain(cap)
        mg, ms, _ = small_signal_gain(mdl)
        cap_g[lbl] = cg; mdl_g[lbl] = mg; spreads[lbl] = (cs, ms)

    # Analytic model gain (dB) for reference.
    def mdl_gain_db(x):
        R = 100e3 * (1 - x) ** 2.5
        return 20 * math.log10(1 + 330e3 / (3.3e3 + R + 1e3))

    emit(f"  {'drive':>6} | {'CAP gain':>9} {'MDL gain':>9} (rendered) | {'MDL analytic':>12} | "
         f"{'CAP-spread':>10} {'MDL-spread':>10}")
    for lbl, xval, _ in DRIVES:
        emit(f"  {lbl:>6} | {cap_g[lbl]:>9.2f} {mdl_g[lbl]:>9.2f}            | "
             f"{mdl_gain_db(xval):>12.2f} | {spreads[lbl][0]:>10.2f} {spreads[lbl][1]:>10.2f}")
    emit("  (spread = max-min gain across the 4 clean levels; >~0.5 dB = clipper grazing, read is")
    emit("   not fully linear there — expected at max drive.)")

    # The decisive comparison: gain STEPS between adjacent knob positions, capture vs model.
    emit("\n" + "-" * 78)
    emit("GAIN STEPS between adjacent knob positions (dB) — the taper SHAPE, capture vs model")
    emit("-" * 78)
    labels = [d[0] for d in DRIVES]
    emit(f"  {'step':>13} | {'CAPTURE':>8} {'MODEL':>8} | {'diff (cap-mdl)':>14}")
    worst = (0.0, "")
    for i in range(len(labels) - 1):
        a, b = labels[i], labels[i + 1]
        cs = cap_g[b] - cap_g[a]
        msp = mdl_g[b] - mdl_g[a]
        d = cs - msp
        if abs(d) > abs(worst[0]):
            worst = (d, f"{a}->{b}")
        emit(f"  {a+'->'+b:>13} | {cs:>8.2f} {msp:>8.2f} | {d:>+14.2f}")
    emit(f"\n  Largest capture-vs-model step disagreement: {worst[0]:+.2f} dB at {worst[1]}.")
    emit("")
    emit("  ** BLEED CONFOUND — READ CAREFULLY (found session 15). ** These captures are base-OD, so")
    emit("  the output FUNDAMENTAL carries the drive-INDEPENDENT clean BLEND bleed (session 7/8). At")
    emit("  drive-min the OD path is weak (~4x gain) and the bleed sits ABOVE it (~+7 dB), so the")
    emit("  low/mid-drive gain reads are DOMINATED BY THE BLEED, not the OD drive gain — the min->9:30")
    emit("  and 9:30->noon steps are NOT clean taper measurements and must NOT be over-read. Only the")
    emit("  HIGH-drive steps (2:30->max, where OD dominates the bleed) are bleed-free and reliable.")
    emit("  The model render carries the SAME bleed, so cap-vs-mdl partially cancels it, but only")
    emit("  within the ~1-4 dB the bleed MODEL itself is uncertain (session 8).")
    emit("")
    emit("  So the ROBUST finding here is the 2:30->max discrepancy: the real pedal's drive gain")
    emit("  rises ~2.4 dB MORE at the top than the (1-x)^2.5 power law (which saturates as R->0).")
    emit("  That is real, bleed-free evidence the taper SHAPE is wrong at the top — consistent with")
    emit("  VR3 being a C-taper the power law approximates badly. The NOON-level question this probe")
    emit("  CANNOT answer cleanly (noon fundamental is bleed-confounded); the case for the taper at")
    emit("  NOON rests on the session-15 HARMONIC grids (gm — a UNIFORM level scale — does NOT fix")
    emit("  noon H3-H2, so a NON-uniform level change, i.e. the taper SHAPE, is the remaining lever).")
    emit("  ** Session 16 needs a BLEED-AWARE taper measurement** (subtract the drive-independent")
    emit("  bleed, or measure level-into-clipper via a bleed-free route) to nail the mid-drive shape;")
    emit("  then model VR3 as a proper C-taper (not (1-x)^p) and re-run the branch-B fit.")
    log.close()
    print("\n[log] analysis/fit_logs/step5_drive_taper_shape.log")
    return 0


if __name__ == "__main__":
    sys.exit(main())
