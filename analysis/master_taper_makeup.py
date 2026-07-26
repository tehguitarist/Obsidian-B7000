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
    # ⚠ ADDED session 41. `ref-clean.wav` IS the master=0.50 member of this very series (_REF_OD
    # with base=clean is every pot at noon, master included) — it was simply never listed here
    # because it doesn't carry a `master-` filename token. It is the best-conditioned interior
    # point on the knob and the ONE the shipped taper is worst at, so leaving it out let a
    # 2.5 dB error sit in the middle of MASTER's travel while the fit reported itself consistent.
    (0.50, "ref-clean.wav"),
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
    """Render the CLEAN chain at a master setting; return sweep_clean RMS. dist-engage forced off.

    ⚠ FIXED 2026-07-27 (session 41): the render must sit in the SAME level frame as `cap_level`,
    which multiplies the capture UP by gain_correction_linear() into the gainSessionDb=0 frame.
    Session 21 taught `render_args()` to emit `--input-trim` for a capture's gain session — a
    correct fix for the matrix, but it silently broke THIS script, which had been written when
    render_args ignored gainSessionDb: the capture was being corrected UP by +12.071 dB while the
    render was being trimmed DOWN by the same amount, a 12 dB double-count landing entirely in
    kOutputMakeup. Clearing the tag on the render template puts both sides at full level again.
    (Cross-checked: the corrected makeup reproduces a direct capture-vs-render level comparison
    on the lvl_ ladder to 0.02 dB.)
    """
    parsed = parse_capture("master-1700_gain-n12_base-clean.wav")  # base-clean knob template
    parsed["master"] = master
    parsed["gainSessionDb"] = 0
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
    for m in (0.25, 0.50, 0.75):
        ratio = lv[m] / lv[1.0]
        p = math.log(ratio) / math.log(m)
        ps.append(p)
        clean = "  (both gain-n12 -> correction CANCELS, cleanest)" if m == 0.75 else ""
        emit(f"  m={m:.2f}: R(m)/R(1.0) = {ratio:.4f} = {20*math.log10(ratio):+.2f} dB  ->  p = {p:.3f}{clean}")
    p_mean = float(np.mean(ps))
    emit(f"  => single-point estimates " + " / ".join(f"{p:.3f}" for p in ps) + f" (mean {p_mean:.3f})")

    # ⚠ Session 41: the two points DISAGREE (1.93 vs 1.73), so a single power law cannot satisfy
    # both — the same finding as the DRIVE C-taper (session 16): a real pot taper is not a power
    # law, and a one-parameter family fitted to ONE point looks exact and is wrong elsewhere.
    # Report the least-squares p over both points and the residual EACH candidate leaves, so the
    # choice is made on the whole knob travel rather than on whichever point was fitted.
    # (m=0.00 is a divider null, 0^p = 0 at every p, and carries no information about p.)
    logs = [(m, 20 * math.log10(lv[m] / lv[1.0])) for m in (0.25, 0.50, 0.75)]
    num = sum((-20 * math.log10(m)) * (-d) for m, d in logs)
    den = sum((20 * math.log10(m)) ** 2 for m, _ in logs)
    p_ls = num / den
    emit(f"  => LEAST-SQUARES over all interior points: p = {p_ls:.3f}")
    emit("")
    emit(f"  {'candidate p':>28} " + " ".join(f"{'err @' + format(m, '.2f'):>10}" for m, _ in logs)
         + f" {'worst':>8}")
    cands = [(p, f"m={m:.2f} point fit") for p, (m, _) in zip(ps, logs)]
    cands += [(p_ls, "least squares (all)"), (2.25, "SHIPPED (= levelTaperExp)")]
    best = None
    for p, label in cands:
        errs = [20 * p * math.log10(m) - d for m, d in logs]
        worst = max(abs(e) for e in errs)
        emit(f"  {label:>28} " + " ".join(f"{e:>+10.2f}" for e in errs) + f" {worst:>8.2f}")
        if best is None or worst < best[0]:
            best = (worst, p, label)
    emit(f"  => on whole-travel error the best of these is {best[2]} (p = {best[1]:.3f}, "
         f"worst {best[0]:.2f} dB)")
    p_fit = p_ls
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
    for m in (0.25, 0.50, 0.75, 1.0):
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
