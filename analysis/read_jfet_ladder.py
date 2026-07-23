#!/usr/bin/env python3.11
"""Phase-7 SESSION 13 — read the drive-min ladder CONFIRM capture (static-vs-dynamic).

Prereq: record `analysis/jfet_ladder_48k.wav` through the pedal at DRIVE-MIN and save the result
as `analysis/captures/jfet_ladder_drive-min.wav` (see the recording notes). Then run this.

It extracts H2(f, level) at 110/220/440 Hz from the capture AND from the static model rendered
through the SAME stimulus at the same drive-min knobs, computes the local slope
p = d log|H2| / d log A_in per frequency, and does the DECISIVE differential `cap_slope -
mdl_slope` (same chain => Gpost/treble/clipper cancel; a corner-localised 110 Hz anomaly => the
C3 degeneration is dynamic). This is the dense-data confirmation of the session-13 STATIC lean.

Run:  /opt/homebrew/bin/python3.11 analysis/read_jfet_ladder.py             (drive-min take)
      /opt/homebrew/bin/python3.11 analysis/read_jfet_ladder.py --drive=noon (bonus drive-noon take)
      (--capture=PATH overrides the capture file; --drive is min|noon or a clock code like 1200)
Log:  analysis/fit_logs/step6_jfet_ladder_confirm[_<drive>].log

The drive-min take is the STATIC-vs-DYNAMIC confirm (the JFET is drive-independent, so this is the
clean JFET measurement). A drive-noon take is NOT for that test — it characterises the clipper +
ceiling×clipper interference vs level/frequency for the phase-aware reshape (the session-12 failure
point). Same reader, different knob; the differential is only a JFET-static verdict at drive-min.
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import signal as sps
import analyze as A
import gen_jfet_ladder as L
from captures import parse_capture, render_args, load_capture, RENDER_BIN

FS = 48000
STIM = "analysis/jfet_ladder_48k.wav"

# drive label -> knob value 0..1. Named endpoints; clock codes (0930/1430/…) resolve via clock_to_x.
DRIVE_KNOB = {"min": 0.0, "noon": 0.5, "max": 1.0}
_args = {a.split("=", 1)[0]: (a.split("=", 1)[1] if "=" in a else "") for a in sys.argv[1:]}
DRIVE = _args.get("--drive", "min")
DRIVE_VAL = DRIVE_KNOB.get(DRIVE, None)
if DRIVE_VAL is None:                       # allow a raw clock code, e.g. --drive=1200
    from analyze import clock_to_x
    DRIVE_VAL = clock_to_x(int(DRIVE))
CAPTURE = _args.get("--capture", f"analysis/captures/jfet_ladder_drive-{DRIVE}.wav")
LOG = f"analysis/fit_logs/step6_jfet_ladder_confirm{'' if DRIVE == 'min' else '_' + DRIVE}.log"
DRIVE_MIN_CAP = "drive-0700_base-od.wav"    # REF-OD knob settings (all else ref, DIST on); drive overridden
TONES = L.LADDER_FREQS
LADDER_DB = L.LADDER_DB
C3_CORNER = 219.0
T = L.segment_times()

FITTED = dict(jfetSatPos=0.24601, jfetSatNeg=2.6099, jfetCeilPos=0.48727,
              jfetCeilNeg=0.27357, clipA0=29.937, clipSatLo=1.2328, clipSatHi=1.5779)
HELD = dict(jfetGm=0.10e-3, jfetRo=200.0e3, jfetRq2=1.0e6,
            levelTaperExp=2.25, driveTaperExp=2.5)


def gpre_db(f, gm=0.10e-3, R4=100e3, R5=1e6, C2=1e-9, R6=3.3e3, C3=220e-9):
    w = 2j * np.pi * f
    hp = (w * (R4 + R5) * C2) / (1 + w * (R4 + R5) * C2)
    div = R5 / (R4 + R5)
    gmR6 = gm * R6
    shelf = (1 + w * R6 * C3) / (1 + w * R6 * C3 / (1 + gmR6))
    return 20 * np.log10(np.abs(hp * div * shelf / (1 + gmR6)) + 1e-30)


def align_to_stim(sig, stim):
    """Integer-sample align `sig` to the stimulus via the 10 s sweep_clean anchor (A.align uses
    the MAIN test signal's segment map, so we correlate on THIS signal's sweep region). Captures
    here are near-sample-aligned (0-3 smp) but model renders carry the OS FIR latency (~64 smp),
    so aligning both keeps the trimmed tone windows honest."""
    a, b = T["sweep_clean"]
    ref = stim[int(a * FS):int(b * FS)]
    s = sig[int(a * FS):int(min(len(sig), (b + 0.5) * FS))]
    n = min(len(ref), len(s))
    corr = sps.correlate(s[:n] - s[:n].mean(), ref[:n] - ref[:n].mean(), mode="full", method="fft")
    lag = int(np.argmax(np.abs(corr))) - (n - 1)
    if lag > 0:
        sig = sig[lag:]
    elif lag < 0:
        sig = np.concatenate([np.zeros(-lag), sig])
    return sig, lag


def seg(sig, name):
    a, b = T[name]
    s = sig[int(a * FS):int(b * FS)]
    m = len(s) // 6
    return s[m:-m]


def h2_of(s, f):
    n = len(s); t = np.arange(n) / FS
    cols = [np.ones(n)]
    for k in range(1, 6):
        cols += [np.cos(2 * np.pi * k * f * t), np.sin(2 * np.pi * k * f * t)]
    M = np.stack(cols, axis=1)
    c, *_ = np.linalg.lstsq(M, s, rcond=None)
    H = [np.hypot(c[1 + 2 * (k - 1)], c[2 + 2 * (k - 1)]) for k in range(1, 6)]
    resid = s - M @ c
    return (20 * np.log10(H[1] / (H[0] + 1e-30) + 1e-30),
            20 * np.log10(H[1] / (np.sqrt(np.mean(resid ** 2)) + 1e-30) + 1e-30))


def render(fits, out):
    parsed = parse_capture(DRIVE_MIN_CAP)
    parsed["drive"] = DRIVE_VAL             # override to the take's drive setting
    extra = []
    for k, v in {**HELD, **fits}.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    subprocess.run([RENDER_BIN, STIM, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    return A.load(out)


def slopes(points):
    pts = sorted(points)   # (a_in, a_eff, h2, dirty)
    out = []
    for (a0, e0, h0, d0), (a1, e1, h1, d1) in zip(pts, pts[1:]):
        if (a1 - a0) > 1e-6:
            out.append((0.5 * (e0 + e1), (h1 - h0) / (a1 - a0), d0 or d1))
    return out


def main():
    if not os.path.exists(CAPTURE):
        print(f"** capture not found: {CAPTURE}")
        print(f"   Record analysis/jfet_ladder_48k.wav through the pedal at DRIVE-{DRIVE.upper()} and")
        print("   save it there first (see the session-13 recording notes). Nothing else to do yet.")
        return
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s):
        print(s); log.write(s + "\n")

    stim = A.load(STIM)
    # NB: use A.load, NOT captures.load_capture — the latter's rate-mislabel guard assumes a 1 kHz
    # cal tone at t=0.5 s, but this stimulus has the align SWEEP there, so it misfires and resamples
    # the whole file into garbage. This ladder signal is recorded correctly at 48 kHz.
    cap = A.load(CAPTURE)
    if not A.is_full_length(cap, stim):
        emit("** capture looks TRUNCATED (< 95% of stimulus length) — re-record before trusting.")
    cap, cap_lag = align_to_stim(cap, stim)
    model, _ = align_to_stim(render(FITTED, "/tmp/jl_full.wav"), stim)
    clip, _ = align_to_stim(
        render({**FITTED, "jfetSatNeg": 0.0, "jfetCeilPos": 1e6, "jfetCeilNeg": 1e6}, "/tmp/jl_clip.wav"), stim)

    emit(f"Session 13 step 6 — drive-{DRIVE} ladder (dense H2 vs level x frequency).")
    emit(f"tones {TONES} Hz, levels {LADDER_DB[0]}..{LADDER_DB[-1]} dBFS (3 dB). capture: {CAPTURE}")
    emit(f"sweep-anchor alignment lag: {cap_lag} samples")
    if DRIVE != "min":
        emit("NOTE: drive != min — the differential below is NOT a JFET-static verdict (the clipper")
        emit("is engaged here); it characterises the clipper + interference vs level for the reshape.\n")
    else:
        emit("")

    series, mseries = {}, {}
    for f in TONES:
        ge = gpre_db(f)
        emit(f"tone {f:g} Hz (Gpre {ge:+.2f}, {'below' if f < C3_CORNER else 'above'} corner):")
        emit(f"  {'A_in':>5} {'A_eff':>6} | {'cap H2':>7} {'capSNR':>6} | {'mdl H2':>7} | "
             f"{'clip H2':>7} | clean?")
        series[f], mseries[f] = [], []
        for db in LADDER_DB:
            nm = f"lad_{f:g}_{db}"
            ch, cs = h2_of(seg(cap, nm), f)
            mh, _ = h2_of(seg(model, nm), f)
            clh, _ = h2_of(seg(clip, nm), f)
            dirty = (ch - clh) < 6.0 or cs < 12.0
            series[f].append((db, db + ge, ch, dirty))
            mseries[f].append((db, db + ge, mh, dirty))
            emit(f"  {db:>5} {db+ge:>6.1f} | {ch:>7.1f} {cs:>6.0f} | {mh:>7.1f} | {clh:>7.1f} | "
                 f"{'yes' if not dirty else 'no'}")

    emit("\n" + "=" * 78)
    emit("DECISIVE — capture slope MINUS model slope, per frequency (clean pts only)")
    emit("=" * 78)
    emit(f"  {'tone':>6} {'corner':>6} | A_eff -> (cap_slope - mdl_slope)")
    dev = {}
    for f in TONES:
        cs = slopes(series[f]); ms = slopes(mseries[f])
        cells, ds = [], []
        for (e, pc, d), (_, pm, _) in zip(cs, ms):
            if d:
                continue
            cells.append(f"{e:+5.1f}->{pc-pm:+4.2f}"); ds.append(pc - pm)
        dev[f] = ds
        emit(f"  {f:>6g} {'below' if f < C3_CORNER else 'above':>6} | "
             f"{'  '.join(cells) if cells else '(none clean)'}")

    below = [abs(x) for f in TONES if f < C3_CORNER for x in dev[f]]
    above = [abs(x) for f in TONES if f >= C3_CORNER for x in dev[f]]
    emit(f"\n  mean |cap-mdl slope|: below-corner {np.mean(below):+.2f} (n={len(below)}), "
         f"above-corner {np.mean(above):+.2f} (n={len(above)})")
    if DRIVE == "min":
        emit("\n  VERDICT (drive-min = JFET-static test):")
        emit("   * below ~ above and both ~0 (<=0.15) => STATIC CONFIRMED => proceed to the")
        emit("     phase-aware ceiling-odd-term reshape (handover §3r).")
        emit("   * below-corner systematically larger / opposite-signed, robust => DYNAMIC => the")
        emit("     JFET needs the coupled-Newton clipper treatment; abandon static-family reshapes.")
    else:
        emit("\n  (drive-noon: this is clipper/interference characterisation, not a static verdict —")
        emit("   a large cap-mdl here just says the current clipper/ceiling fit is off at this drive,")
        emit("   which is expected and is what the phase-aware reshape will address.)")
    log.close()
    print(f"\n[log] {LOG}")


if __name__ == "__main__":
    main()
