#!/usr/bin/env python3.11
"""Phase-7 SESSION 17 — fit masterTaperExp + calibrate kOutputMakeup (the LAST two constants).

CLEAN-PATH ISOLATION. The `master-*_base-clean` captures are DIST-DISENGAGED, so BLEND is forced to
100% clean: the JFET + CD4049 clipper are BYPASSED entirely. And kInputRef CANCELS in the linear path
(GainStaging.h §1). So masterTaperExp and kOutputMakeup depend on NEITHER the fitted clipper/JFET
family NOR kInputRef — only on the EQ/MASTER linear stages. That is why they are the last, cleanest
step, and why fitting them now (before the fitted family is written into FitParams.h) is valid.

(1) masterTaperExp p — NO RENDER NEEDED. The MASTER pot is a pure post-EQ divider (MasterOut.h):
    output(m) = Ntop(EQ) * divRatio(m),  divRatio(m) = m^p,  and divRatio(1)=1 (unity at full CW).
    So the SHAPE ratio cancels the master-independent Ntop AND the makeup:
        R_cap(m) / R_cap(1.0) = m^p   ->   p = ln(R_cap(m)/R_cap(1.0)) / ln(m)
    Estimated at the two interior knobs (0.25, 0.75); master=0.0 is a null (0^p=0, uninformative).
    ⚠ GAIN-n12: master-1430/1700 were captured -12 dB (interface headroom); apply the measured
    +12.071 dB correction (captures.gain_correction_linear). Both 0.75 and 1.0 are gain-n12, so their
    correction CANCELS in R(0.75)/R(1.0) — that estimate needs no correction and is the cleaner one.

(2) kOutputMakeup — ONE render. At master=1.0 (divRatio=1, taper-independent) render the CLEAN chain
    with makeup=1, match its level to the (gain-corrected) capture:
        kOutputMakeup = R_cap(1.0) / R_mdl(1.0; makeup=1)
    Then VERIFY at 0.25/0.75 that the model (with fitted p + makeup) matches the captures within ~1 dB
    — a consistency check the fit did not target.

Level metric: RMS over the 'sweep_clean' segment (clean, well-defined, no clipping on this path; it is
also the alignment anchor). Captures are integer-aligned to the reference before the segment read.

Run:  /opt/homebrew/bin/python3.11 analysis/master_taper_makeup.py
Log:  analysis/fit_logs/step7_master_taper_makeup.log
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
from captures import parse_capture, render_args, gain_correction_linear, RENDER_BIN

FS = 48000
ORIG = "analysis/test_signal_48k.wav"
LOG = "analysis/fit_logs/step7_master_taper_makeup.log"

# master knob -> capture. 0.0 is a divider null (uninformative for p); kept for reporting.
MASTERS = [
    (0.00, "master-0700_base-clean.wav"),
    (0.25, "master-0930_base-clean.wav"),
    (0.75, "master-1430_gain-n12_base-clean.wav"),
    (1.00, "master-1700_gain-n12_base-clean.wav"),
]
CAPDIR = "analysis/captures"
DRIVE_TAPER = 1.98        # session-17 measured (held); irrelevant on the clean path but kept consistent


def seg_rms(sig):
    """RMS over the sweep_clean segment of an aligned signal."""
    a, b = A.T["sweep_clean"]
    s = sig[int(a * FS):int(b * FS)]
    return float(np.sqrt(np.mean(s.astype(np.float64) ** 2)))


def cap_level(name):
    """Gain-corrected sweep_clean RMS of a capture, aligned to the reference."""
    parsed = parse_capture(name)
    x = A.load(f"{CAPDIR}/{name}") * gain_correction_linear(parsed)
    xa, _ = A.align(x, A.load(ORIG))
    return seg_rms(xa)


def render_clean_level(master, taper_p, makeup):
    """Render the CLEAN chain at a master setting; return sweep_clean RMS. dist-engage forced off."""
    parsed = parse_capture("master-1700_gain-n12_base-clean.wav")  # base-clean knob template
    parsed["master"] = master
    extra = ["--fit", f"masterTaperExp={taper_p:.6g}", "--fit", f"driveTaperExp={DRIVE_TAPER:.6g}"]
    out = f"/tmp/mtm_{int(master*100):03d}.wav"
    subprocess.run([RENDER_BIN, ORIG, out, "--os", "4", "--output-makeup", f"{makeup:.9g}"]
                   + render_args(parsed, extra), check=True, capture_output=True)
    r, _ = A.align(A.load(out), A.load(ORIG))
    return seg_rms(r)


def main():
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 90)
    emit("MASTER taper (masterTaperExp) + output makeup (kOutputMakeup) — session 17")
    emit("=" * 90)
    emit("Clean-path isolation: DIST off => clipper/JFET bypassed; kInputRef cancels. Depends only on")
    emit("the EQ/MASTER linear stages. Level = RMS over the sweep_clean segment (gain-n12 corrected).")
    emit("")

    # ---- capture levels ---------------------------------------------------------------
    emit("-" * 90)
    emit("CAPTURE LEVELS (sweep_clean RMS, gain-n12 corrected)")
    emit("-" * 90)
    lv = {}
    for m, name in MASTERS:
        if not os.path.exists(f"{CAPDIR}/{name}"):
            emit(f"  ** MISSING {name}")
            return 2
        r = cap_level(name)
        lv[m] = r
        parsed = parse_capture(name)
        gc = 20 * math.log10(gain_correction_linear(parsed))
        emit(f"  master {m:.2f}  {name:40s}  RMS {20*math.log10(r+1e-12):+7.2f} dBFS "
             f"(gain-corr {gc:+.1f} dB)")
    emit("")

    # ---- (1) taper exponent p ---------------------------------------------------------
    emit("-" * 90)
    emit("(1) masterTaperExp p   [ divRatio(m) = m^p ;  p = ln(R(m)/R(1.0)) / ln(m) ]")
    emit("-" * 90)
    ps = []
    for m in (0.25, 0.75):
        ratio = lv[m] / lv[1.0]
        p = math.log(ratio) / math.log(m)
        ps.append(p)
        clean = "  (both gain-n12 -> correction CANCELS, cleanest)" if m == 0.75 else ""
        emit(f"  m={m:.2f}: R(m)/R(1.0) = {ratio:.4f} = {20*math.log10(ratio):+.2f} dB  ->  p = {p:.3f}{clean}")
    p_fit = ps[1]          # prefer the 0.75/1.0 estimate (gain-corr cancels); 0.25 corroborates
    p_mean = float(np.mean(ps))
    emit(f"  => two estimates {ps[0]:.3f} / {ps[1]:.3f}; PREFER the gain-n12-cancelling 0.75/1.0: "
         f"p = {p_fit:.3f}  (mean {p_mean:.3f})")
    emit(f"  shipped interim was 1.43; A-taper pots typically p ~ 2-3. A pin-free interior value that")
    emit(f"  both knobs agree on is the accept condition.")
    emit("")

    # ---- (2) output makeup ------------------------------------------------------------
    emit("-" * 90)
    emit("(2) kOutputMakeup   [ render CLEAN at master=1.0, makeup=1, match the capture ]")
    emit("-" * 90)
    r_mdl_10 = render_clean_level(1.0, p_fit, 1.0)
    makeup = lv[1.0] / r_mdl_10
    emit(f"  R_cap(1.0)          = {20*math.log10(lv[1.0]+1e-12):+7.2f} dBFS")
    emit(f"  R_mdl(1.0,makeup=1) = {20*math.log10(r_mdl_10+1e-12):+7.2f} dBFS")
    emit(f"  => kOutputMakeup = R_cap/R_mdl = {makeup:.4f}  ({20*math.log10(makeup):+.2f} dB)")
    emit(f"  (calibration §2: makeup MAY exceed 1.0 — do NOT pad for headroom.)")
    emit("")

    # ---- (3) consistency check at the interior knobs ----------------------------------
    emit("-" * 90)
    emit("(3) CONSISTENCY — model (fitted p + makeup) vs capture at each master (the fit did NOT")
    emit("    target absolute level here, so agreement is real corroboration)")
    emit("-" * 90)
    emit(f"  {'master':>7} | {'capture':>9} {'model':>9} {'err dB':>7}")
    worst = 0.0
    for m in (0.25, 0.75, 1.0):
        r_mdl = render_clean_level(m, p_fit, makeup)
        e = 20 * math.log10((r_mdl + 1e-12) / (lv[m] + 1e-12))
        worst = max(worst, abs(e))
        emit(f"  {m:>7.2f} | {20*math.log10(lv[m]+1e-12):>+8.2f} {20*math.log10(r_mdl+1e-12):>+8.2f} {e:>+7.2f}")
    emit(f"  worst |err| = {worst:.2f} dB  ({'OK (<1 dB)' if worst < 1.0 else 'CHECK — taper/makeup mismatch'})")
    emit("")

    emit("=" * 90)
    emit("RESULT — write these into the shipped defaults")
    emit("=" * 90)
    emit(f"  MasterOut.h  kMasterTaperExp  : 1.43 -> {p_fit:.3f}")
    emit(f"  GainStaging.h kOutputMakeupNominal : 0.90 -> {makeup:.3f}")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
