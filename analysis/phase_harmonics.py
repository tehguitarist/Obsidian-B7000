#!/usr/bin/env python3.11
"""Phase-7 SESSION 13, step 1 — PHASE-AWARE harmonic analysis of the drive-min tones.

WHY (handover §3o(1)): sessions 7-12 fit AMPLITUDE-only data and were each killed by a
measurement the objective could not see. Session 12 established (from AMPLITUDES) that the
model's JFET drain-current ceiling H3 and the clipper H3 are ANTI-PHASE, so softening the
clipper cancels total H3 instead of raising it. The unanswered question that decides the
whole session-13 branch: does the REAL pedal's low-drive H3 phase OPPOSE the clipper's (so
the model's ceiling has the right sign and is merely too big) or MATCH it (so the model's
ceiling odd term is BACKWARDS and no magnitude tweak fixes it)?

THE TOOL: extract COMPLEX harmonics H_n = |H_n| e^{i phi_n} from a steady tone, then report
the SHIFT-INVARIANT relative phase

        psi_n = phi_n - n * phi_1                                    (degrees)

A whole-segment time shift tau multiplies X(f) by e^{-i 2 pi f tau}, so phi_1 -> phi_1 - w1 tau
and phi_n -> phi_n - n w1 tau; psi_n is invariant. That immunises it against the 0-26-sample
cross-capture alignment lags flagged in session 8 (the reason cross-capture phase was declared
untrustworthy). We VERIFY that invariance numerically on a synthetic shifted tone before
trusting it on captures (--verify).

Harmonics are extracted by a SIMULTANEOUS least-squares fit to
    x(t) ~ c0 + sum_n [ c_n cos(2 pi n f0 t) + s_n sin(2 pi n f0 t) ]      (n = 1..NMAX)
with t measured from the analysis window's first sample. This is exact for a non-integer
period (220 Hz @ 48 kHz is 218.18 samples), leakage-free between harmonics (all fit jointly),
and shares ONE time origin across harmonics so the psi_n shift-invariance holds exactly.

THE THREE SOURCES compared, all at DRIVE-MIN, all read AT THE OUTPUT through the full chain
(so each carries whatever downstream linear phase rotation it actually experiences — the same
thing the capture's H3 experiences):
  * CAPTURE      drive-0700_base-od.wav                              (the real pedal)
  * MODEL ceiling-only   clipper made ~linear (clipSatLo/Hi huge) -> only the JFET ceiling
                         (odd term L*tanh(w/L)) makes H3
  * MODEL clipper-only   JFET ceiling disabled (jfetCeilPos/Neg = 1e6) -> only the clipper
                         makes H3 (JFET even bump makes H2 only)
The model's two sources should come out ~180 deg apart (re-deriving session 12's amplitude
interference finding from PHASE — an internal consistency check). Then:
  capture psi3 ~ clipper-only psi3   -> real H3 is on the CLIPPER side  -> ceiling BACKWARDS
  capture psi3 ~ ceiling-only psi3   -> real H3 is on the CEILING side  -> ceiling right sign,
                                                                           just too big

Run:
  /opt/homebrew/bin/python3.11 analysis/phase_harmonics.py --verify   (self-test only)
  /opt/homebrew/bin/python3.11 analysis/phase_harmonics.py            (full measurement)
Log: analysis/fit_logs/step5_phase_harmonics.log
"""
import sys, os, subprocess
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
import analyze as A
from captures import parse_capture, render_args, load_capture, RENDER_BIN

FS = 48000
NMAX = 6
CAP = "analysis/captures"
DRIVE_MIN_CAP = "drive-0700_base-od.wav"

# Tones to analyse (Hz). Chosen for H3 SNR: 110/220/440 keep H2..H3 well inside the SK-LPF
# passband; 1000 is marginal (H3 = 3 kHz sits on the 3.3 kHz SK corner) and reported but not
# leaned on. 220 sits ON C3's 219 Hz degeneration-bypass corner (the static-vs-dynamic suspect).
TONES = [110.0, 220.0, 440.0, 1000.0]

# Session-11 fitted point (the operating point where the interference was characterised — see
# step4b_clipk_interference.log). FIT_KEYS order: s, a, cp, cn, clipA0, clipSatLo, clipSatHi.
FITTED = dict(jfetSatPos=0.24601, jfetSatNeg=2.6099, jfetCeilPos=0.48727,
              jfetCeilNeg=0.27357, clipA0=29.937, clipSatLo=1.2328, clipSatHi=1.5779)
# Held (identical to fit_nonlinear.HELD): gm, taper, level taper, ro/rq2.
HELD = dict(jfetGm=0.10e-3, jfetRo=200.0e3, jfetRq2=1.0e6,
            levelTaperExp=2.25, driveTaperExp=2.5)


# ------------------------------------------------------------------------------------------
def fit_harmonics(seg, f0, fs=FS, nmax=NMAX):
    """Simultaneous LS fit -> complex harmonics H[1..nmax] (H[n] = c_n - i s_n so that the
    real signal component at n f0 is |H[n]| cos(2 pi n f0 t + phi_n), phi_n = angle(H[n]))."""
    n = len(seg)
    t = np.arange(n) / fs
    cols = [np.ones(n)]
    for k in range(1, nmax + 1):
        cols.append(np.cos(2 * np.pi * k * f0 * t))
        cols.append(np.sin(2 * np.pi * k * f0 * t))
    M = np.stack(cols, axis=1)
    coef, *_ = np.linalg.lstsq(M, seg, rcond=None)
    H = np.zeros(nmax + 1, dtype=complex)
    for k in range(1, nmax + 1):
        c = coef[1 + 2 * (k - 1)]
        s = coef[2 + 2 * (k - 1)]
        H[k] = c - 1j * s            # x = c cos + s sin = Re{(c - i s) e^{i w t}}
    resid = seg - M @ coef
    return H, coef, resid


def rel_phase(H):
    """psi_n = phi_n - n phi_1 (deg), wrapped to (-180, 180]. psi_1 == 0 by construction."""
    phi1 = np.angle(H[1])
    psi = np.zeros(len(H))
    for n in range(1, len(H)):
        psi[n] = np.degrees(_wrap(np.angle(H[n]) - n * phi1))
    return psi


def _wrap(rad):
    return (rad + np.pi) % (2 * np.pi) - np.pi


def harm_db(H):
    """|H_n| re fundamental, dB."""
    return np.array([20 * np.log10(abs(H[n]) / (abs(H[1]) + 1e-30) + 1e-30)
                     for n in range(len(H))])


def steady_window(seg):
    """Trim the outer 1/6 each side (fade + smoother settle) of a tone segment."""
    m = len(seg) // 6
    return seg[m:-m]


# ------------------------------------------------------------------------------------------
def verify_invariance():
    """Numerically confirm psi_n is invariant under a whole-segment time shift (integer AND
    fractional), on a synthetic tone with KNOWN relative phases, before trusting it on captures."""
    print("=" * 78)
    print("SELF-TEST — shift-invariance of psi_n = phi_n - n*phi_1")
    print("=" * 78)
    f0 = 220.0
    n = int(0.6 * FS)
    t = np.arange(n) / FS
    # Known harmonics with deliberately non-trivial relative phases.
    amps = {1: 1.0, 2: 0.10, 3: 0.03, 4: 0.01}
    phis = {1: 0.7, 2: -2.1, 3: 1.3, 4: 0.4}      # radians (absolute)
    def synth(tau_samples):
        tt = (np.arange(n) + tau_samples) / FS
        x = np.zeros(n)
        for k, a in amps.items():
            x += a * np.cos(2 * np.pi * k * f0 * tt + phis[k])
        return x
    true_psi = {k: np.degrees(_wrap(phis[k] - k * phis[1])) for k in amps}
    print(f"  true psi (deg):  " + "  ".join(f"psi{k}={true_psi[k]:+7.2f}" for k in sorted(amps)))
    ok = True
    for tau in [0.0, 1.0, 7.0, 26.0, 3.7, -12.4]:   # integer + fractional (incl. session-8's 26)
        seg = synth(tau)
        H, _, _ = fit_harmonics(seg, f0)
        psi = rel_phase(H)
        errs = [abs(_deg_err(psi[k], true_psi[k])) for k in sorted(amps)]
        maxerr = max(errs)
        ok = ok and maxerr < 0.5
        print(f"  tau={tau:+6.1f} smp: " + "  ".join(f"psi{k}={psi[k]:+7.2f}" for k in sorted(amps))
              + f"   max|err|={maxerr:.3f} deg")
    print(f"\n  INVARIANCE {'CONFIRMED' if ok else '** FAILED **'} "
          f"(all shifts recover psi within 0.5 deg)\n")
    return ok


def _deg_err(a, b):
    return np.degrees(_wrap(np.radians(a - b)))


# ------------------------------------------------------------------------------------------
HOT_IN = "/tmp/ph_hot_test.wav"       # ORIG scaled up so the JFET ceiling actually engages
HOT_DB = 10.0                          # -14 dBFS tones -> -4 dBFS (vgs peak ~0.126 -> ~0.4 V)


def make_hot_input():
    """A +HOT_DB copy of the test signal. Used ONLY to reveal the model's H3 SOURCE phases:
    at drive-min small-signal the JFET ceiling makes NO isolable H3 (it sits at the numerical
    floor), so its phase is unmeasurable there. The ceiling odd term is drive-INDEPENDENT and
    its H3 phase (intrinsic shape sign + fixed downstream linear rotation) is amplitude-stable,
    so a hotter input reads the SAME phase, just measurably. Magnitudes here are NOT comparable
    to the capture; only phases are used."""
    x = A.load(A.ORIG)
    g = 10 ** (HOT_DB / 20.0)
    from scipy.io import wavfile
    wavfile.write(HOT_IN, FS, (x * g).astype(np.float32))


def render_variant(cap, fits, out, inp=None):
    parsed = parse_capture(cap)
    extra = []
    for k, v in {**HELD, **fits}.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    subprocess.run([RENDER_BIN, inp or A.ORIG, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    return A.load(out)


def measure(sig, label, log):
    """Report |Hn| and psi_n at every TONE for a rendered/captured full signal."""
    rows = {}
    for f0 in TONES:
        name = f"tone_{f0:g}"
        seg = steady_window(A.seg_of(sig, name))
        H, coef, resid = fit_harmonics(seg, f0)
        hd = harm_db(H)
        psi = rel_phase(H)
        # phase SNR: residual RMS re fundamental
        nf = 20 * np.log10(np.sqrt(np.mean(resid ** 2)) / (abs(H[1]) + 1e-30) + 1e-30)
        rows[f0] = dict(H=H, hd=hd, psi=psi, nf=nf)
    _print_block(label, rows, log)
    return rows


def _print_block(label, rows, log):
    def emit(s):
        print(s); log.write(s + "\n")
    emit(f"\n--- {label} ---")
    emit(f"  {'tone':>6} | {'H2dB':>6} {'H3dB':>6} {'H4dB':>6} | "
         f"{'psi2':>7} {'psi3':>7} {'psi4':>7} | {'noise':>6}")
    for f0 in TONES:
        r = rows[f0]
        emit(f"  {f0:>6g} | {r['hd'][2]:>6.1f} {r['hd'][3]:>6.1f} {r['hd'][4]:>6.1f} | "
             f"{r['psi'][2]:>7.1f} {r['psi'][3]:>7.1f} {r['psi'][4]:>7.1f} | {r['nf']:>6.1f}")


def main():
    if "--verify" in sys.argv:
        verify_invariance()
        if len([a for a in sys.argv[1:] if not a.startswith("-")]) == 0 and "--full" not in sys.argv:
            return
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open("analysis/fit_logs/step5_phase_harmonics.log", "w")
    log.write("Session 13 step 1 — phase-aware harmonic analysis (drive-min).\n")
    log.write("psi_n = phi_n - n*phi_1 (deg), shift-invariant; LS complex-harmonic fit.\n")

    inv_ok = verify_invariance()
    log.write(f"\nshift-invariance self-test: {'PASS' if inv_ok else 'FAIL'}\n")

    def emit(s):
        print(s); log.write(s + "\n")

    SNR_MIN = 12.0     # a psi_n is only trusted when |H3| exceeds the residual floor by this

    emit("\n" + "=" * 78)
    emit("TRAP FOUND (why the ceiling cannot be isolated by 'high clipSat'):")
    emit("  The clipper's D1/D2 clamp window TRACKS satLo (Clipper.h: clampHi = 9.6 - satLo,")
    emit("  clampLo = -0.6 - satLo). So clipSat >~ 10 makes the window ~[-1e4,-1e4], FREEZING")
    emit("  node W -> the clipper becomes a DC source, and the only tone left at the output is")
    emit("  the harmonic-free clean BLEND bleed (H2/H3 at the -168 dB floor). The plan's")
    emit("  'ceiling-only via clipper at high sat' technique is INVALID. Isolations used here:")
    emit("   * clipper-only  = jfetCeilPos/Neg = 1e6 (ceiling off, clipper NORMAL) — VALID.")
    emit("   * ceiling contribution = COHERENT COMPLEX subtraction full - clipper-only among")
    emit("     the aligned model renders (same chain latency), NOT a separate render.")
    emit("=" * 78)

    # 1) The real pedal, drive-min. THE reference to explain.
    cap = load_capture(f"{CAP}/{DRIVE_MIN_CAP}")
    cap_rows = measure(cap, f"CAPTURE  {DRIVE_MIN_CAP}", log)

    # 2) Model, full (fitted point) — apples-to-apples with the capture (real -14 dBFS tones).
    full_rows = measure(render_variant(DRIVE_MIN_CAP, FITTED, "/tmp/ph_full.wav"),
                        "MODEL full (session-11 fitted point, -14 dBFS)", log)

    # 3) Model, clipper-only (ceiling off, clipper NORMAL) at -14 (capture-comparable) AND at
    #    a HOT input (the clipper's H3 SNR at -14 is poor; HOT reads the same intrinsic phase).
    clip_fits = dict(FITTED); clip_fits["jfetCeilPos"] = 1e6; clip_fits["jfetCeilNeg"] = 1e6
    clip14_rows = measure(render_variant(DRIVE_MIN_CAP, clip_fits, "/tmp/ph_clip14.wav"),
                          "MODEL clipper-only, -14 dBFS (ceiling off, clipper normal)", log)
    make_hot_input()
    cliphot_rows = measure(render_variant(DRIVE_MIN_CAP, clip_fits, "/tmp/ph_cliphot.wav", HOT_IN),
                           f"MODEL clipper-only, HOT +{HOT_DB:g} dB (clipper H3 at good SNR)", log)

    # ---- Ceiling contribution by COHERENT complex subtraction (aligned model renders) ----
    # full and clipper-only are rendered through the SAME chain at the same OS -> identical
    # latency -> their RAW complex H are directly subtractable. ceiling_H3 = H3_full - H3_clipoff.
    emit("\n" + "=" * 78)
    emit("MODEL H3 DECOMPOSITION — complex, per tone (deg = phase re that render's own phi1,")
    emit("i.e. psi3; |.| = dB re fundamental). ceiling = full - clipper (coherent).")
    emit("=" * 78)
    emit(f"  {'tone':>6} | {'full |H3|':>9} {'psi3':>7} | {'clip |H3|':>9} {'psi3':>7} | "
         f"{'ceil |H3|':>9} {'psi3':>7} | {'ceil<->clip':>11}")
    ceil_psi3 = {}
    for f0 in TONES:
        Hf = full_rows[f0]['H']; Hc = clip14_rows[f0]['H']
        # bring both into the psi frame using the FULL render's phi1 (common reference)
        phi1 = np.angle(Hf[1])
        H3f = Hf[3] * np.exp(-1j * 3 * phi1)       # psi-framed full H3 phasor
        H3c = Hc[3] * np.exp(-1j * 3 * np.angle(Hc[1]))
        # coherent subtraction must use a COMMON phi1 reference; re-derive clip in full's frame
        H3c_inFull = Hc[3] * np.exp(-1j * 3 * phi1)
        H3ceil = H3f - H3c_inFull
        f1db = 20 * np.log10(abs(Hf[1]) + 1e-30)
        d_full = 20 * np.log10(abs(Hf[3]) / abs(Hf[1]) + 1e-30)
        d_clip = 20 * np.log10(abs(Hc[3]) / abs(Hc[1]) + 1e-30)
        d_ceil = 20 * np.log10(abs(H3ceil) / abs(Hf[1]) + 1e-30)
        p_full = np.degrees(np.angle(H3f))
        p_clip = np.degrees(np.angle(H3c))
        p_ceil = np.degrees(np.angle(H3ceil))
        ceil_psi3[f0] = p_ceil
        emit(f"  {f0:>6g} | {d_full:>9.1f} {p_full:>7.1f} | {d_clip:>9.1f} {p_clip:>7.1f} | "
             f"{d_ceil:>9.1f} {p_ceil:>7.1f} | {abs(_deg_err(p_ceil, p_clip)):>10.1f}")
    emit("  (ceil<->clip ~ 180 deg re-derives session-12's anti-phase interference from PHASE.)")

    # ---- Verdict: capture psi3 vs ceiling contribution vs clipper -------------------------
    # H3 of a 220 Hz tone lands at 660 Hz — right on the IC2_B bridged-T notch (~717 Hz), whose
    # DEPTH the linear model gets wrong (circuit.md: model -28 dB vs capture -3.4 dB), so its
    # PHASE there is unreliable. Flag any tone whose 3rd harmonic sits in [560,860] Hz.
    emit("\n" + "=" * 78)
    emit("VERDICT — capture H3 phase vs the model's ceiling and clipper contributions")
    emit("=" * 78)
    emit(f"  {'tone':>6} | {'H3 Hz':>6} | {'cap psi3':>9} {'capSNR':>6} | {'ceil':>7} {'clip':>7} | "
         f"{'cap<->ceil':>10} {'cap<->clip':>10} | verdict")
    verdicts = []
    for f0 in TONES:
        h3hz = 3 * f0
        cp = cap_rows[f0]['psi'][3]
        capsnr = cap_rows[f0]['hd'][3] - cap_rows[f0]['nf']
        ce = ceil_psi3[f0]
        cl = cliphot_rows[f0]['psi'][3]        # HOT clipper: best-SNR clipper phase reference
        clsnr = cliphot_rows[f0]['hd'][3] - cliphot_rows[f0]['nf']
        d_ceil = abs(_deg_err(cp, ce))
        d_clip = abs(_deg_err(cp, cl))
        notch = 560.0 <= h3hz <= 860.0
        resolvable = abs(_deg_err(ce, cl)) > 90.0
        flags = []
        if notch: flags.append("H3@notch")
        if capsnr < SNR_MIN: flags.append("capSNR")
        if clsnr < SNR_MIN: flags.append("clipSNR")
        if not resolvable: flags.append("refs<90")
        if flags:
            v = "(inconclusive: " + ",".join(flags) + ")"
        else:
            v = "CEILING (right sign)" if d_ceil < d_clip else "CLIPPER (ceiling BACKWARDS)"
            verdicts.append(v.split()[0])
        emit(f"  {f0:>6g} | {h3hz:>6g} | {cp:>9.1f} {capsnr:>6.0f} | {ce:>7.0f} {cl:>7.0f} | "
             f"{d_ceil:>10.0f} {d_clip:>10.0f} | {v}")

    emit("\n  Reading:")
    emit("   * capture near CEILING phase  -> model ceiling odd term has the RIGHT sign, just")
    emit("     too big -> a ceiling-magnitude reshape can work.")
    emit("   * capture near CLIPPER phase  -> model ceiling odd term is BACKWARDS -> magnitude")
    emit("     tweak cannot fix it; a phase-aware fit target is mandatory.")
    emit("   * verdict DIFFERING across (clean) tones = the nonlinear H3 phase is")
    emit("     FREQUENCY-DEPENDENT -> direct evidence for the static-vs-dynamic test (step 2).")
    tally = {v: verdicts.count(v) for v in set(verdicts)}
    emit(f"\n  Conclusive tones: {tally if tally else 'NONE — all flagged/inconclusive'}")
    log.close()
    print("\n[log] analysis/fit_logs/step5_phase_harmonics.log")


if __name__ == "__main__":
    main()
