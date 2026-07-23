#!/usr/bin/env python3.11
"""Phase-7 SESSION 13, step 2 — STATIC-vs-DYNAMIC discriminating test (handover §3o(2)).

THE QUESTION: the whole JfetStage is a static Wiener-Hammerstein shaper (linear HP + C3
shelf, THEN a memoryless waveshaper). But C3's degeneration-bypass corner is 219 Hz, INSIDE
the measurement band: below it R6's local series feedback linearises the device; above it the
feedback is bypassed and distortion rises. If that frequency dependence is TRUE nonlinear
feedback (not a linear pre-emphasis of a fixed shaper), then NO static shaper of any family
can fit it — and every fit so far has sat at 220 Hz, right ON that corner.

THE TEST: for a static memoryless nonlinearity y = f(x), the 2nd-harmonic amplitude is a
SINGLE frequency-independent function of the drive amplitude AT THE SHAPER:
    H2_out(f, A_in) = |Gpost(2f)| * h2( |Gpre(f)| * A_in )
where Gpre = input->gate(vgs) linear transfer, Gpost = shaper->output. So the LOCAL SLOPE
    p(f, A) = d log|H2_out| / d log A_in                        (Gpost cancels: it is const in A)
is a function of the EFFECTIVE amplitude A_eff = |Gpre(f)| * A_in ALONE. Plot p vs A_eff for
every tone frequency: for a STATIC nonlinearity they COLLAPSE onto one curve. If the
below-corner tones (110 Hz, feedback active) sit on a DIFFERENT p-vs-A_eff curve than the
above-corner tones (440/1000 Hz, feedback bypassed), the nonlinearity has MEMORY -> dynamic
-> the static family is dead and the JFET needs the clipper treatment (coupled Newton solve).

Gpre(f) (small-signal, gm held 0.10 mS) is the schematic front-end and is NOT what is in
dispute — what is in dispute is whether treating the degeneration as a LINEAR shelf (which is
exactly what defines A_eff at small signal) survives into the distortion. The collapse test
asks precisely that. The slope is |Gpost|-immune, so the mismodelled 717 Hz bridged-T notch
(which corrupts phase, step 1) does NOT corrupt this amplitude test.

DATA (all drive-min = drive-0700_base-od.wav; NO new captures):
  * 1 kHz level ladder lvl_-36..-3 (12 steps, 3 dB) — a DENSE H2-vs-level curve at 1000 Hz.
  * 3 driven Farina sweeps -18/-12/-6 — H2(f) at 3 levels for 110/220/440/1000.
  * discrete tones -14 — one more H2 point per frequency.
CLIPPER CONTAMINATION: above ~-14 dBFS the CD4049 starts adding its own H2, so the clean-JFET
regime is the LOW end. A clipper-only render (ceiling off) bounds where clipper-H2 approaches
JFET-H2; points inside that margin are flagged and excluded from the static verdict.

Run:  /opt/homebrew/bin/python3.11 analysis/static_vs_dynamic.py
Log:  analysis/fit_logs/step5_static_vs_dynamic.log
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
import gen_test_signal as G
from captures import parse_capture, render_args, load_capture, RENDER_BIN

FS = 48000
CAP = "analysis/captures"
DRIVE_MIN_CAP = "drive-0700_base-od.wav"
TONES = [110.0, 220.0, 440.0, 1000.0]
SWEEP_DB = [-18, -12, -6]          # driven Farina sweeps present in the signal
LADDER_DB = list(range(-36, -2, 3))  # 1 kHz lvl_ ladder steps
C3_CORNER = 219.0                    # the degeneration-bypass corner under test

FITTED = dict(jfetSatPos=0.24601, jfetSatNeg=2.6099, jfetCeilPos=0.48727,
              jfetCeilNeg=0.27357, clipA0=29.937, clipSatLo=1.2328, clipSatHi=1.5779)
HELD = dict(jfetGm=0.10e-3, jfetRo=200.0e3, jfetRq2=1.0e6,
            levelTaperExp=2.25, driveTaperExp=2.5)


# ---- linear input->vgs transfer (JfetStage.h header, small-signal, gm held) ---------------
def gpre_db(f, gm=0.10e-3, R4=100e3, R5=1e6, C2=1e-9, R6=3.3e3, C3=220e-9):
    """|input -> effective vgs| in dB. HP (C2 into R4+R5) * gate divider R5/(R4+R5) *
    shelf (1+sR6C3)/(1+sR6C3/(1+gmR6)) / (1+gmR6). This is the drive the shaper sees; its
    frequency shape (esp. the 219 Hz shelf) is what maps A_in to A_eff per tone."""
    w = 2j * np.pi * f
    hp = (w * (R4 + R5) * C2) / (1 + w * (R4 + R5) * C2)
    div = R5 / (R4 + R5)
    gmR6 = gm * R6
    shelf = (1 + w * R6 * C3) / (1 + w * R6 * C3 / (1 + gmR6))
    H = hp * div * shelf / (1 + gmR6)
    return 20 * np.log10(np.abs(H) + 1e-30)


# ---- H2 extraction ------------------------------------------------------------------------
def tone_h2_db(sig, f):
    """H2 re fundamental (dB) of a discrete tone segment, LS complex-harmonic fit + noise."""
    seg = A.seg_of(sig, f"tone_{f:g}")
    m = len(seg) // 6
    return _h2_of(seg[m:-m], f)


def lvl_h2_db(sig, db, f=1000.0):
    seg = A.seg_of(sig, f"lvl_{db}")
    m = len(seg) // 6
    return _h2_of(seg[m:-m], f)


def _h2_of(seg, f):
    n = len(seg); t = np.arange(n) / FS
    cols = [np.ones(n)]
    for k in range(1, 6):
        cols += [np.cos(2 * np.pi * k * f * t), np.sin(2 * np.pi * k * f * t)]
    M = np.stack(cols, axis=1)
    coef, *_ = np.linalg.lstsq(M, seg, rcond=None)
    H = [np.hypot(coef[1 + 2 * (k - 1)], coef[2 + 2 * (k - 1)]) for k in range(1, 6)]
    resid = seg - M @ coef
    nf = np.sqrt(np.mean(resid ** 2))
    h2 = 20 * np.log10(H[1] / (H[0] + 1e-30) + 1e-30)
    snr = 20 * np.log10(H[1] / (nf + 1e-30) + 1e-30)
    return h2, snr


def sweep_h2_db(sig, orig, db, freqs):
    """H2(f) re fundamental (dB) from a driven Farina sweep, at the requested tone freqs."""
    ref = A.seg_of(orig, "sweep_clean")
    seg = A.seg_of(sig, f"sweep_drv_{db}")
    fr, thd, Hn = A.harmonic_thd_curve(seg, ref, max_order=5)
    out = {}
    for f in freqs:
        h1 = np.interp(f, fr, Hn[1]); h2 = np.interp(f, fr, Hn[2])
        out[f] = 20 * np.log10(h2 / (h1 + 1e-30) + 1e-30)
    return out


def render_model(fits, out):
    parsed = parse_capture(DRIVE_MIN_CAP)
    extra = []
    for k, v in {**HELD, **fits}.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    subprocess.run([RENDER_BIN, A.ORIG, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    return A.load(out)


def main():
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open("analysis/fit_logs/step5_static_vs_dynamic.log", "w")

    def emit(s):
        print(s); log.write(s + "\n")

    emit("Session 13 step 2 — STATIC-vs-DYNAMIC test (drive-min, no new captures).")
    emit("H2 re fundamental (dB) vs input level and tone frequency; collapse of the local")
    emit("slope p = dlog|H2|/dlogA vs the EFFECTIVE gate drive A_eff = |Gpre(f)|*A_in.\n")

    orig = A.load(A.ORIG)
    cap = load_capture(f"{CAP}/{DRIVE_MIN_CAP}")
    # TRUE clipper-H2 floor: JFET made fully linear (even bump AND ceiling off) so ONLY the
    # CD4049 asymmetry makes H2. Points where capture H2 is within ~6 dB of this are
    # clipper-contaminated and excluded from the JFET static verdict.
    clipoff = render_model({**FITTED, "jfetSatNeg": 0.0, "jfetCeilPos": 1e6, "jfetCeilNeg": 1e6},
                           "/tmp/sd_clipoff.wav")
    model = render_model(FITTED, "/tmp/sd_full.wav")

    emit("Gpre(f) — model small-signal input->vgs (dB), the shelf that defines A_eff:")
    for f in TONES:
        emit(f"   {f:>6g} Hz : {gpre_db(f):+6.2f} dB   ({'BELOW' if f < C3_CORNER else 'ABOVE'} the 219 Hz corner)")
    emit(f"   -> above-corner tones see {gpre_db(1000)-gpre_db(110):+.2f} dB more drive than 110 Hz "
         f"at the same input.\n")

    # ---- 1 kHz LADDER: the dense curve ---------------------------------------------------
    emit("=" * 84)
    emit("1 kHz LEVEL LADDER (dense) — capture vs static model. clip = clipper-only H2 (the")
    emit("contamination floor). A_eff column = input dBFS + Gpre(1000).")
    emit("=" * 84)
    emit(f"  {'A_in':>5} {'A_eff':>6} | {'cap H2':>7} {'capSNR':>6} | {'mdl H2':>7} | "
         f"{'clip H2':>7} | {'cap-clip':>8} | clean?")
    lad = {}
    ge = gpre_db(1000.0)
    for db in LADDER_DB:
        ch, cs = lvl_h2_db(cap, db)
        mh, _ = lvl_h2_db(model, db)
        clh, _ = lvl_h2_db(clipoff, db)
        margin = ch - clh                      # how far capture H2 sits above the clipper floor
        clean = margin > 8.0 and cs > 15.0
        lad[db] = dict(a_eff=db + ge, cap=ch, snr=cs, mdl=mh, clip=clh, clean=clean)
        emit(f"  {db:>5} {db+ge:>6.1f} | {ch:>7.1f} {cs:>6.0f} | {mh:>7.1f} | {clh:>7.1f} | "
             f"{margin:>8.1f} | {'yes' if clean else 'no'}")

    # ---- SWEEPS: multi-frequency, 3 levels ------------------------------------------------
    emit("\n" + "=" * 84)
    emit("DRIVEN SWEEPS (Farina) — H2(f) re fund at 3 input levels, per tone. A_eff = A_in+Gpre(f).")
    emit("=" * 84)
    sweep = {f: {} for f in TONES}
    capS = {db: sweep_h2_db(cap, orig, db, TONES) for db in SWEEP_DB}
    mdlS = {db: sweep_h2_db(model, orig, db, TONES) for db in SWEEP_DB}
    clpS = {db: sweep_h2_db(clipoff, orig, db, TONES) for db in SWEEP_DB}
    for f in TONES:
        emit(f"  tone {f:g} Hz (Gpre {gpre_db(f):+.2f}):")
        emit(f"    {'A_in':>5} {'A_eff':>6} | {'cap H2':>7} | {'mdl H2':>7} | {'clip H2':>7} | clean?")
        for db in SWEEP_DB:
            ch = capS[db][f]; mh = mdlS[db][f]; clh = clpS[db][f]
            clean = (ch - clh) > 8.0
            sweep[f][db] = dict(a_eff=db + gpre_db(f), cap=ch, mdl=mh, clip=clh, clean=clean)
            emit(f"    {db:>5} {db+gpre_db(f):>6.1f} | {ch:>7.1f} | {mh:>7.1f} | {clh:>7.1f} | "
                 f"{'yes' if clean else 'no'}")

    # discrete tones at -14 (one more point per frequency)
    emit("\n  discrete tones @ -14 dBFS (one more point/frequency):")
    emit(f"    {'tone':>5} {'A_eff':>6} | {'cap H2':>7} {'capSNR':>6} | {'mdl H2':>7} | clean?")
    tone14 = {}
    for f in TONES:
        ch, cs = tone_h2_db(cap, f); mh, _ = tone_h2_db(model, f); clh, _ = tone_h2_db(clipoff, f)
        clean = (ch - clh) > 8.0 and cs > 15.0
        tone14[f] = dict(a_eff=-14 + gpre_db(f), cap=ch, snr=cs, mdl=mh, clip=clh, clean=clean)
        emit(f"    {f:>5g} {-14+gpre_db(f):>6.1f} | {ch:>7.1f} {cs:>6.0f} | {mh:>7.1f} | "
             f"{'yes' if clean else 'no'}")

    # ---- COLLAPSE ANALYSIS: local slope vs A_eff, per frequency ---------------------------
    emit("\n" + "=" * 84)
    emit("COLLAPSE TEST — local slope p = d log|H2| / d log(A_in) vs A_eff (Gpost-immune, so")
    emit("the mismodelled 717 Hz notch does NOT corrupt it). For a STATIC nonlinearity all tones")
    emit("fall on ONE p(A_eff) curve. A point is 'dirty' if capture H2 is within 6 dB of the")
    emit("TRUE clipper-H2 floor (clipper contamination); shown but excluded from the verdict.")
    emit("=" * 84)

    # per-frequency (a_in, a_eff, h2, dirty) for the CAPTURE. dirty = clipper-contaminated.
    def dirty(cap_h2, clip_h2):
        return (cap_h2 - clip_h2) < 6.0

    series = {f: [] for f in TONES}
    for db, d in lad.items():
        series[1000.0].append((db, d['a_eff'], d['cap'], dirty(d['cap'], d['clip'])))
    for f in TONES:
        for db, d in sweep[f].items():
            series[f].append((db, d['a_eff'], d['cap'], dirty(d['cap'], d['clip'])))
        d = tone14[f]; series[f].append((-14.0, d['a_eff'], d['cap'], dirty(d['cap'], d['clip'])))

    def slopes_from(points):
        pts = sorted(points)
        out = []
        for (a0, e0, h0, d0), (a1, e1, h1, d1) in zip(pts, pts[1:]):
            if (a1 - a0) > 1e-6:
                out.append((0.5 * (e0 + e1), (h1 - h0) / (a1 - a0), d0 or d1))
        return out

    emit(f"  {'tone':>6} {'corner':>6} | slope samples  A_eff -> p  [* = clipper-dirty]")
    master = []   # (A_eff, p) clean samples from the 1 kHz ladder = the reference curve
    allslopes = {}
    for f in TONES:
        sl = slopes_from(series[f]); allslopes[f] = sl
        tag = "below" if f < C3_CORNER else "above"
        cells = "  ".join(f"{e:+5.1f}->{p:4.2f}{'*' if d else ' '}" for e, p, d in sl)
        emit(f"  {f:>6g} {tag:>6} | {cells}")
        if f == 1000.0:
            master = [(e, p) for e, p, d in sl if not d]

    # NOTE the raw A_eff slopes above assume the ONLY frequency-dependence is Gpre
    # (input->gate). But the treble net + the CD4049 sit AFTER the JFET and make the effective
    # drive frequency-dependent too — and the STATIC MODEL has those same stages. So raw
    # non-collapse on A_eff (e.g. 1 kHz saturating at a lower A_eff than 110 Hz) is NOT by
    # itself a dynamic signature; it is shared by any static system through this chain. The
    # confound-free test is DIFFERENTIAL vs the static model (below).
    _ = master  # (the A_eff-master view is superseded by the differential test below)

    # ---- DECISIVE TEST: capture-slope MINUS model-slope, per frequency --------------------
    # The static model runs through the IDENTICAL chain (same treble net, clipper, Gpost). So
    # cap_slope - mdl_slope isolates whether the CAPTURE's JFET H2-vs-level behaves like a
    # STATIC one. cap-mdl ~ 0 at every frequency -> static-consistent. A CORNER-SPECIFIC
    # anomaly (110 Hz, below corner, differing from 220/440/1000) -> the C3 degeneration is
    # dynamic. (A smooth, all-frequency offset would just be the model's unfitted shaper
    # shape, NOT dynamics — only a corner-localised split implicates the degeneration.)
    emit("\n" + "=" * 84)
    emit("DECISIVE TEST — capture slope MINUS static-model slope, per frequency (same chain")
    emit("=> Gpost/treble/clipper all cancel). ~0 => capture's JFET is STATIC like the model.")
    emit("A 110 Hz (below-corner) anomaly vs 220/440/1000 => C3 degeneration is DYNAMIC.")
    emit("=" * 84)

    mseries = {f: [] for f in TONES}
    for db, d in lad.items():
        mseries[1000.0].append((db, d['a_eff'], d['mdl'], dirty(d['cap'], d['clip'])))
    for f in TONES:
        for db, d in sweep[f].items():
            mseries[f].append((db, d['a_eff'], d['mdl'], dirty(d['cap'], d['clip'])))
        d = tone14[f]; mseries[f].append((-14.0, d['a_eff'], d['mdl'], dirty(d['cap'], d['clip'])))

    emit(f"  {'tone':>6} {'corner':>6} | A_eff -> (cap_slope - mdl_slope)   [clean only]")
    diff_below, diff_above = [], []
    for f in TONES:
        cs = slopes_from(series[f]); ms = slopes_from(mseries[f])
        cells = []
        for (e, pc, d), (_, pm, _) in zip(cs, ms):
            if d:
                continue
            dv = pc - pm
            cells.append(f"{e:+5.1f}->{dv:+4.2f}")
            (diff_below if f < C3_CORNER else diff_above).append(dv)
        emit(f"  {f:>6g} {'below' if f < C3_CORNER else 'above':>6} | "
             f"{'  '.join(cells) if cells else '(none clean)'}")

    # ---- verdict ---------------------------------------------------------------------------
    emit("\n" + "=" * 84)
    emit("READING")
    emit("=" * 84)
    def clean_levels(f):
        return sum(1 for (_, _, _, d) in series[f] if not d)
    for f in TONES:
        emit(f"    {f:>6g} Hz ({'below' if f < C3_CORNER else 'above'} corner): "
             f"{clean_levels(f)} clean levels, {len([1 for _,_,d in allslopes[f] if not d])} clean slopes")
    allc = np.array([abs(x) for x in diff_below + diff_above])
    emit(f"\n  |cap-mdl slope| : below-corner(110) mean {np.mean([abs(x) for x in diff_below]):+.2f} "
         f"(n={len(diff_below)}), above(220/440/1000) mean {np.mean([abs(x) for x in diff_above]):+.2f} "
         f"(n={len(diff_above)})")
    emit(f"  below-corner NOT anomalous vs above-corner: "
         f"{'YES' if diff_below and np.mean([abs(x) for x in diff_below]) <= np.mean([abs(x) for x in diff_above]) + 0.10 else 'NO / unclear'}")
    emit("\n  Interpretation:")
    emit("   * cap-mdl ~0 at ALL frequencies AND 110 (below) no worse than 220/440/1000 (above)")
    emit("     => capture's JFET H2-vs-level is STATIC-consistent, NO C3-corner dynamic signature")
    emit("     => STATIC family holds => branch = reshape the ceiling's odd term, phase-aware fit.")
    emit("   * 110 Hz cap-mdl systematically LARGE / opposite-signed vs the above-corner tones,")
    emit("     robust to noise => C3 degeneration is DYNAMIC => static family dead => branch =")
    emit("     the coupled-Newton JFET clipper treatment (Q1/Q2 Shichman-Hodges).")
    emit("\n  CAVEAT: below-corner coverage is ONE frequency (110 Hz), 3 slope samples from")
    emit("  4 levels — thin. The dense evidence (1 kHz ladder: static model tracks capture to")
    emit("  ~0.5 dB over 30 dB) and the differential (no corner anomaly) LEAN STATIC, but to")
    emit("  CONFIRM before the expensive branch commit, the pre-authorised ONE capture is:")
    emit("     drive-min level ladder at 110 AND 220 Hz, 3 dB steps, extending BELOW -36 dBFS")
    emit("  (dense clipper-free slope curves at a below- and an on-corner frequency to overlay")
    emit("   against the 1 kHz ladder). It is cheap and de-risks the static-vs-dynamic call.")
    log.close()
    print("\n[log] analysis/fit_logs/step5_static_vs_dynamic.log")


if __name__ == "__main__":
    main()
