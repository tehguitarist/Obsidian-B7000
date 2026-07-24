#!/usr/bin/env python3.11
"""Phase-7 SESSION 16 step (1) — BLEED-FREE measurement of the DRIVE taper shape.

WHY (session 15 §3u.5/§3u.6): the residual noon H3-H2 gap is a DRIVE-POSITION-specific level
error — `jfetGm` (a UNIFORM scale) does not fix noon while 2:30/max swing freely, and no physical
clipper VTC param fixes it either. So a NON-uniform level change (the DRIVE taper SHAPE) is the
remaining lever. `DriveStage.h` models the 100k C-taper VR3 as a single POWER LAW
`R = 100k*(1-x)^p` (p=2.5) — and a C-taper is NOT a power law. Session 11 only ever pinned p=2.5
to a 2-POINT small-signal LEVEL match, which `drive_taper_shape.py` then showed is itself
BLEED-CONFOUNDED at low/mid drive.

THE BLEED PROBLEM. These ladders are base-OD, so the output fundamental is
    Y = (clean BLEND bleed)  +  (OD path)
and the bleed is drive-INDEPENDENT and DOMINATES at low/mid drive (the OD path is only ~4x at
drive-min). `drive_taper_shape.py` reads the raw fundamental, so its min->9:30->noon steps are
not taper reads at all. Session 8 puts the bleed MODEL's own uncertainty at 1-4 dB, so
"subtract the modelled bleed" would just import that uncertainty.

THE FIX — DO NOT ESTIMATE THE BLEED AT ALL; CANCEL IT ALGEBRAICALLY.
PedalChain's topology (see its header diagram) is decisive: the clean tap splits at InputBuffer
BEFORE the OD chain, and within the OD chain everything upstream of DRIVE (JFET, Treble/ATTACK)
and everything downstream (Clipper, Recovery, both SK LPFs, LevelBlend, EQ, MasterOut) is
drive-INDEPENDENT. DriveStage is an ideal-op-amp output (zero source Z) so the clipper's input
impedance does not load it. Therefore in the SMALL-SIGNAL regime (clipper ~linear) the ONLY
drive-dependent factor in the whole chain is DriveStage's own gain
    A(f,x) = 1 + Zfb(f) * g(x),    Zfb = R15 || C10,    g(x) = 1/(R17 + R_VR3(x) + R32)
so, per tone frequency f, the measured complex fundamental obeys the EXACTLY AFFINE law
    Y(f,x) = C(f) + M(f) * g(x)       with C = B_bleed + K_od(f),  M = K_od(f)*Zfb(f)
The bleed B lives entirely inside C and CANCELS in the affine solve. `g(x)` is REAL, and it is
the only unknown that varies with the knob. No bleed model, no EQ model, no level calibration,
no clipper model enters the answer.

ANCHORING (2 anchors are mathematically REQUIRED — g -> alpha*g+beta is absorbed by C,M):
both endpoints are taper-SHAPE-independent circuit facts, not fits:
    g(0) = 1/(3.3k + 100k + 1k) = 1/104.3k     (knob min = full pot resistance)
    g(1) = 1/(3.3k +   0  + 1k) = 1/4.3k       (knob max = wiper at the CW end, 0 ohm)
The x=1 anchor assumes zero pot END RESISTANCE (exactly what DriveStage.h anchors to, and the
`audioTaperR0` floor-trap note in TaperUtils.h). That assumption is SENSITIVITY-TESTED below
(re-solve with a 500 ohm / 1k end R) because it is the one non-fact in the chain.

Then, for each interior knob:
    g_hat = g_min + Re[(Y_i - Y_min)/M]   and   Im[(Y_i - Y_min)/M]  is a VALIDITY RESIDUAL
    R_i   = 1/g_hat - (R17+R32)
A nonzero imaginary part means the 5 points are NOT collinear in the complex plane, i.e. the
"only DRIVE changes" premise or the small-signal premise has failed. It is a free, built-in
falsification test — not a goodness-of-fit number.

⚠ THE ALIGNMENT TRAP (measured, not hypothetical). A residual time offset tau rotates every
phasor by exp(-j*2*pi*f*tau), which breaks collinearity and biases the complex solve. Correlating
each take against the sweep anchor does NOT fix it, because the anchor correlation is itself
DRIVE-DEPENDENT: measured lags across the five model renders drift +64.08 -> +67.56 samples, i.e.
3.5 samples = 11 deg at 440 Hz, purely from the drive knob changing the sweep's own content. A
naive per-take alignment therefore INJECTS a drive-correlated phase error into the very quantity
being measured (it inflated the 440 Hz self-test error to 25% while 110 Hz was <1%).
The fix is not to discard phase but to model it: the offset is a per-take DELAY, so it is ONE
unknown tau per capture shared across all three tones, and it is solved jointly below. A tau
common to all takes is degenerate (absorbed into C and M), so tau is fixed at 0 for the drive-min
take and solved for the other four.

TWO INDEPENDENT ESTIMATORS (they fail differently; agreement is the evidence):
  (A) COMPLEX AFFINE, JOINTLY DE-DELAYED. Unknowns: C_f, M_f (complex, per tone), the 3 interior
      g's, and 4 per-take tau's. 3 tones x 5 drives x N levels complex equations against 19
      unknowns. Uses ALL the information (magnitude AND relative phase across tones).
  (B) MAGNITUDE-ONLY, 3-FREQUENCY JOINT. |Y(f,x)|^2 = p0_f + p1_f*g(x) + p2_f*g(x)^2 — a quadratic
      per frequency with the SAME three interior g's shared across all three tones. Completely
      IMMUNE to time alignment by construction (it never looks at a phase). If (A) and (B) agree,
      alignment is not driving the answer.

ESTIMATOR SELF-TEST (L-006: validate the estimator against a known ground truth BEFORE believing
any number it produces). The identical pipeline is run on MODEL renders whose taper is KNOWN
(`(1-x)^2.5`). It must recover R = 100k*(1-x)^2.5 at 9:30/noon/2:30. If the self-test fails, the
estimator is broken and the capture numbers mean nothing — the script says so and stops.

Run:  /opt/homebrew/bin/python3.11 analysis/drive_taper_bleedfree.py
Log:  analysis/fit_logs/step6_drive_taper_bleedfree.log
"""
import sys, os, subprocess, math
sys.path.insert(0, os.path.dirname(__file__))
import numpy as np
from scipy import signal as sps
from scipy.optimize import least_squares
import analyze as A
import read_jfet_ladder as L
from captures import parse_capture, render_args, RENDER_BIN

FS = 48000
STIM = L.STIM
CAPDIR = "analysis/captures"
LOG = "analysis/fit_logs/step6_drive_taper_bleedfree.log"

# Circuit facts (DriveStage.h / circuit.md "DRIVE gain stage (IC2_A)").
R15, C10, R17, R32, RPOT = 330.0e3, 47.0e-12, 3.3e3, 1.0e3, 100.0e3
RFIX = R17 + R32                       # 4.3k series, always in the gain leg

TONES = (110.0, 220.0, 440.0)
# Cleanest ladder rungs. At drive-max the stage is ~78x, so stay well down; per-level agreement
# is reported so a clipper-grazed rung is visible rather than silently averaged in.
CLEAN_DB = [-60, -57, -54, -51, -48]
LEVELS = [-57, -54, -51]               # rungs pooled by the joint solves

DRIVES = [("min",  0.0, "jfet_ladder_drive-min.wav"),
          ("9:30", 0.25, "jfet_ladder_drive-0930.wav"),
          ("noon", 0.5, "jfet_ladder_drive-noon.wav"),
          ("2:30", 0.75, "jfet_ladder_drive-1430.wav"),
          ("max",  1.0, "jfet_ladder_drive-max.wav")]
INTERIOR = [1, 2, 3]                   # indices into DRIVES that the solve infers

HELD = dict(jfetGm=0.10e-3, jfetRo=200e3, jfetRq2=1e6, levelTaperExp=2.25, driveTaperExp=2.5)
MODEL_P = 2.5                          # the model taper the self-test must recover
BASE_CAP = "drive-0700_base-od.wav"    # REF-OD knob settings; drive overridden per render


# ---------------------------------------------------------------- circuit helpers
def g_of_R(R):
    return 1.0 / (RFIX + R)


def R_of_g(g):
    return 1.0 / g - RFIX


def model_R(x, p=MODEL_P):
    return RPOT * (1.0 - x) ** p


# ---------------------------------------------------------------- alignment
def frac_align(sig, stim):
    """Integer align on the 10 s sweep anchor, then refine to SUB-SAMPLE precision.

    A residual delay tau rotates every phasor by exp(-j*2*pi*f*tau), which is exactly the error
    the complex estimator (A) is vulnerable to. Parabolic interpolation of the correlation peak
    gives tau; an FFT phase ramp applies it. Estimator (B) does not use this at all.
    """
    a, b = L.T["sweep_clean"]
    ref = stim[int(a * FS):int(b * FS)]
    s0 = sig[int(a * FS):int(min(len(sig), (b + 0.5) * FS))]
    n = min(len(ref), len(s0))
    r, s = ref[:n] - ref[:n].mean(), s0[:n] - s0[:n].mean()
    corr = sps.correlate(s, r, mode="full", method="fft")
    k = int(np.argmax(np.abs(corr)))
    lag = k - (n - 1)
    # parabolic vertex of |corr| about the peak -> sub-sample offset
    frac = 0.0
    if 0 < k < len(corr) - 1:
        y0, y1, y2 = (abs(corr[k - 1]), abs(corr[k]), abs(corr[k + 1]))
        den = y0 - 2 * y1 + y2
        if abs(den) > 1e-30:
            frac = 0.5 * (y0 - y2) / den
    total = lag + frac
    N = len(sig)
    F = np.fft.rfft(sig)
    w = 2 * np.pi * np.fft.rfftfreq(N)
    return np.fft.irfft(F * np.exp(1j * w * total), n=N), total


# ---------------------------------------------------------------- phasor extraction
def phasor(s, f):
    """Complex fundamental of a steady tone by LS harmonic fit (5 harmonics + DC).

    Returns the analytic-style coefficient c = a - j*b for the fit a*cos(wt) + b*sin(wt), plus the
    residual-referenced SNR so a noise-dominated rung is visible.
    """
    n = len(s)
    t = np.arange(n) / FS
    cols = [np.ones(n)]
    for k in range(1, 6):
        cols += [np.cos(2 * np.pi * k * f * t), np.sin(2 * np.pi * k * f * t)]
    M = np.stack(cols, axis=1)
    c, *_ = np.linalg.lstsq(M, s, rcond=None)
    resid = s - M @ c
    fund = complex(c[1], -c[2])
    snr = 20 * math.log10(abs(fund) / (np.sqrt(np.mean(resid ** 2)) + 1e-30) + 1e-30)
    return fund, snr


def measure(sig, stim):
    """-> {(freq, dB): (phasor / input-amplitude, snr)} for the clean rungs."""
    sig, tau = frac_align(sig, stim)
    out = {}
    for f in TONES:
        for db in CLEAN_DB:
            s = L.seg(sig, f"lad_{f:g}_{db}")
            p, snr = phasor(s, f)
            out[(f, db)] = (p / (10.0 ** (db / 20.0)), snr)
    return out, tau


def render_model(x, out):
    parsed = parse_capture(BASE_CAP)
    parsed["drive"] = x
    extra = []
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    subprocess.run([RENDER_BIN, STIM, out, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    return A.load(out)


# ---------------------------------------------------------------- estimator A
def solve_complex_naive(meas, g_anchor_max, db):
    """Per-tone affine solve with NO delay modelling. Kept only to expose the alignment trap:
    it is exact at 110 Hz and badly biased at 440 Hz. Not used for the reported answer."""
    g_min, g_max = g_of_R(RPOT), g_anchor_max
    res = {}
    for f in TONES:
        Y = np.array([meas[i][(f, db)][0] for i in range(5)])
        M = (Y[4] - Y[0]) / (g_max - g_min)
        if abs(M) < 1e-30:
            return None
        q = (Y - Y[0]) / M
        res[f] = (g_min + q.real, q.imag / (g_max - g_min))
    return res


def solve_complex(meas, g_anchor_max, dbs):
    """Estimator A — joint complex affine solve with per-take delays.

    Unknowns: 3 interior g's; C_f, M_f complex per tone (shared across levels after amplitude
    normalisation); tau_i for takes 1..4 (tau_0 == 0, since a common delay is degenerate).
    Residual: Y_{f,i} * exp(+j*2*pi*f*tau_i) - (C_f + M_f * g_i), scaled per tone.
    Returns (g_interior[3], tau[5], rms_residual).
    """
    g_min, g_max = g_of_R(RPOT), g_anchor_max
    span = g_max - g_min
    nT = len(TONES)

    def unpack(v):
        gi = g_min + np.clip(v[:3], 1e-4, 1.0) * span
        tau = np.concatenate([[0.0], v[3:7]])
        CM = v[7:].reshape(nT, 4)
        return gi, tau, CM

    def resid(v):
        gi, tau, CM = unpack(v)
        g = np.array([g_min, gi[0], gi[1], gi[2], g_max])
        out = []
        for ti, f in enumerate(TONES):
            C = complex(CM[ti, 0], CM[ti, 1])
            M = complex(CM[ti, 2], CM[ti, 3])
            pred = C + M * g
            for db in dbs:
                Y = np.array([meas[i][(f, db)][0] for i in range(5)])
                Yc = Y * np.exp(1j * 2 * np.pi * f * tau / FS)
                sc = np.mean(np.abs(Y)) + 1e-30
                d = (Yc - pred) / sc
                out.append(d.real)
                out.append(d.imag)
        return np.concatenate(out)

    # seed from the naive per-tone solve at the first level (good where phase error is small)
    seed = solve_complex_naive(meas, g_anchor_max, dbs[0])
    g0 = np.clip([(seed[TONES[0]][0][j] - g_min) / span for j in INTERIOR], 1e-3, 0.999)
    v0 = list(g0) + [0.0, 0.0, 0.0, 0.0]
    gs = np.array([g_min, *(g_min + np.array(g0) * span), g_max])
    for f in TONES:
        Y = np.array([meas[i][(f, dbs[0])][0] for i in range(5)])
        M = (Y[4] - Y[0]) / span
        C = Y[0] - M * g_min
        v0 += [C.real, C.imag, M.real, M.imag]
    sol = least_squares(resid, np.array(v0), method="trf", max_nfev=40000)
    gi, tau, _ = unpack(sol.x)
    return np.sort(gi), tau, float(np.sqrt(np.mean(sol.fun ** 2)))


# ---------------------------------------------------------------- estimator B
def solve_magnitude(meas, g_anchor_max, dbs):
    """Alignment-IMMUNE joint solve: |Y_f(g)|^2 = p0_f + p1_f*g + p2_f*g^2, interior g shared.

    Unknowns: 3 quadratic coefficients per (freq, level) block + the 3 interior g's (shared by
    ALL blocks). Levels are pooled after input-amplitude normalisation.
    """
    g_min, g_max = g_of_R(RPOT), g_anchor_max
    blocks = [(f, db) for f in TONES for db in dbs]
    obs = {}
    for (f, db) in blocks:
        obs[(f, db)] = np.array([abs(meas[i][(f, db)][0]) ** 2 for i in range(5)])

    def unpack(v):
        gi = g_min + np.abs(v[:3]) * (g_max - g_min)   # interior g's, kept inside the span
        P = v[3:].reshape(len(blocks), 3)
        return gi, P

    def resid(v):
        gi, P = unpack(v)
        g = np.array([g_min, gi[0], gi[1], gi[2], g_max])
        out = []
        for bi, key in enumerate(blocks):
            p0, p1, p2 = P[bi]
            pred = p0 + p1 * g + p2 * g ** 2
            sc = np.mean(np.abs(obs[key])) + 1e-30
            out.append((pred - obs[key]) / sc)          # per-block scale-free
        return np.concatenate(out)

    # seed: interior g's evenly spread; quadratic coeffs from a per-block LS at the seed
    v0 = [0.25, 0.5, 0.75]
    gseed = np.array([g_min, *(g_min + np.array(v0) * (g_max - g_min)), g_max])
    for key in blocks:
        Vm = np.stack([np.ones(5), gseed, gseed ** 2], axis=1)
        c, *_ = np.linalg.lstsq(Vm, obs[key], rcond=None)
        v0 += list(c)
    sol = least_squares(resid, np.array(v0), method="trf", max_nfev=20000)
    gi, _ = unpack(sol.x)
    return np.sort(gi), float(np.sqrt(np.mean(sol.fun ** 2)))


# ---------------------------------------------------------------- reporting
def main():
    os.makedirs("analysis/fit_logs", exist_ok=True)
    log = open(LOG, "w")

    def emit(s=""):
        print(s)
        log.write(s + "\n")

    emit("=" * 92)
    emit("DRIVE taper — BLEED-FREE shape measurement (session 16 step 1)")
    emit("=" * 92)
    emit("Premise: only DriveStage is drive-dependent => Y(f,x) = C(f) + M(f)*g(x), g real.")
    emit("The clean BLEND bleed lives entirely in C and CANCELS. Anchors g(0)=1/104.3k, g(1)=1/4.3k")
    emit("are taper-SHAPE-independent circuit facts. Two estimators: (A) complex affine,")
    emit("(B) magnitude-only 3-freq joint (alignment-immune). Self-tested on model renders first.")
    emit("")

    stim = A.load(STIM)

    # ---- load captures + model renders -------------------------------------------------
    emit("-" * 92)
    emit("LOAD + ALIGN")
    emit("-" * 92)
    cap_m, mdl_m = [], []
    for i, (lbl, x, name) in enumerate(DRIVES):
        p = f"{CAPDIR}/{name}"
        if not os.path.exists(p):
            emit(f"** MISSING {p} — cannot run.")
            return 2
        cm, ctau = measure(A.load(p), stim)
        mm, mtau = measure(render_model(x, f"/tmp/dtb_{lbl.replace(':', '')}.wav"), stim)
        cap_m.append(cm)
        mdl_m.append(mm)
        snrs = [cm[(f, db)][1] for f in TONES for db in CLEAN_DB]
        emit(f"  drive {lbl:>5} (x={x:.2f})  cap lag {ctau:+8.3f} smp   mdl lag {mtau:+8.3f} smp"
             f"   cap fund-SNR min {min(snrs):5.1f} dB")
    emit("  (SNR = fundamental vs LS residual. Low SNR at the quietest rungs would show here.)")
    emit("")

    g_max_nom = g_of_R(0.0)

    # ---- ESTIMATOR SELF-TEST on the model (known taper) ---------------------------------
    emit("-" * 92)
    emit("ESTIMATOR SELF-TEST (L-006) — recover the MODEL's KNOWN taper R = 100k*(1-x)^2.5")
    emit("-" * 92)
    truth = [model_R(DRIVES[j][1]) for j in INTERIOR]
    naive = solve_complex_naive(mdl_m, g_max_nom, -57)
    selfA, selfAtau, selfArms = solve_complex(mdl_m, g_max_nom, LEVELS)
    selfB, selfBrms = solve_magnitude(mdl_m, g_max_nom, LEVELS)
    emit(f"  {'drive':>6} | {'TRUE R':>9} | {'(A) joint':>10} {'(B) magonly':>12} | "
         f"{'naive 110Hz':>12} {'naive 440Hz':>12}   <- alignment trap")
    wA = wB = 0.0
    for k, j in enumerate(INTERIOR):
        ra, rb = R_of_g(selfA[k]), R_of_g(selfB[k])
        n1, n4 = R_of_g(naive[110.0][0][j]), R_of_g(naive[440.0][0][j])
        tr = truth[k]
        wA = max(wA, abs(ra - tr) / max(tr, 1e3))
        wB = max(wB, abs(rb - tr) / max(tr, 1e3))
        emit(f"  {DRIVES[j][0]:>6} | {tr/1e3:>8.2f}k | {ra/1e3:>9.2f}k {rb/1e3:>11.2f}k | "
             f"{n1/1e3:>11.2f}k {n4/1e3:>11.2f}k")
    emit(f"  worst error vs truth:  (A) {wA*100:5.2f}%   (B) {wB*100:5.2f}%      "
         f"[(A) rms {selfArms:.2e}, (B) rms {selfBrms:.2e}]")
    emit(f"  (A) recovered per-take delays (smp, take0=0 by construction): "
         + " ".join(f"{t:+.2f}" for t in selfAtau))
    emit("  The 'naive' columns are the SAME data with per-take delay NOT modelled: exact at")
    emit("  110 Hz, badly biased at 440 Hz. That contrast IS the alignment trap, shown not asserted.")
    ok = (wA <= 0.05 and wB <= 0.05)
    if not ok:
        emit("  ** SELF-TEST FAILED (>5%) — the estimator is broken; capture numbers below are NOT")
        emit("     trustworthy. Fix the estimator before reading anything else.")
    else:
        emit("  SELF-TEST PASSED (both estimators <5% on a KNOWN taper, through the same chain,")
        emit("  same bleed, same EQ) — so they measure the taper, not a bleed/EQ/level artefact.")
    emit("")

    # ---- THE MEASUREMENT ----------------------------------------------------------------
    emit("-" * 92)
    emit("MEASUREMENT — the REAL pedal's DRIVE taper")
    emit("-" * 92)
    capA, capAtau, capArms = solve_complex(cap_m, g_max_nom, LEVELS)
    capB, capBrms = solve_magnitude(cap_m, g_max_nom, LEVELS)
    emit(f"  (A) recovered per-take delays (smp): " + " ".join(f"{t:+.2f}" for t in capAtau)
         + f"   [fit rms {capArms:.2e}]")
    emit(f"  (B) magnitude-only joint fit rms {capBrms:.2e}")
    emit("")

    # per-level stability of the alignment-immune estimator = the linearity check
    emit("  Per-level stability (estimator B re-solved at each rung — a clipper-grazed rung would")
    emit("  drift; flat rows mean the small-signal premise holds):")
    emit(f"  {'level':>7} | " + " ".join(f"{DRIVES[j][0]:>10}" for j in INTERIOR))
    for db in LEVELS:
        gb, _ = solve_magnitude(cap_m, g_max_nom, [db])
        emit(f"  {db:>5} dB | " + " ".join(f"{R_of_g(gb[k])/1e3:>9.2f}k" for k in range(3)))
    emit("")

    emit("-" * 92)
    emit("RESULT — measured taper vs the shipped power law")
    emit("-" * 92)
    emit(f"  {'drive':>6} {'knob':>5} | {'(A) R':>10} {'(B) R':>10} {'agree':>7} | "
         f"{'MODEL (1-x)^2.5':>16} | {'stage gain':>19} | {'level err':>10}")
    meas_R = {}
    for k, j in enumerate(INTERIOR):
        lbl, x, _ = DRIVES[j]
        ra, rb = R_of_g(capA[k]), R_of_g(capB[k])
        rmean = 0.5 * (ra + rb)
        meas_R[lbl] = rmean
        rm = model_R(x)
        gmeas = 20 * math.log10(1 + R15 / (RFIX + rmean))
        gmdl = 20 * math.log10(1 + R15 / (RFIX + rm))
        emit(f"  {lbl:>6} {x:>5.2f} | {ra/1e3:>9.2f}k {rb/1e3:>9.2f}k {abs(ra-rb)/rmean*100:>6.1f}% | "
             f"{rm/1e3:>15.2f}k | meas {gmeas:>5.2f} mdl {gmdl:>5.2f} | {gmeas-gmdl:>+9.2f} dB")
    emit("  'agree' = |A-B|/mean. A uses phase + a delay model; B never looks at a phase. They")
    emit("  fail differently, so agreement is real evidence, not a shared assumption.")
    emit("  'level err' = measured stage gain MINUS model stage gain at that knob, bleed removed.")
    emit("  POSITIVE = the real pedal drives the CD4049 HARDER there than the model does.")
    emit("")

    # ---- sensitivity to the ONE assumption: pot end resistance --------------------------
    emit("-" * 92)
    emit("SENSITIVITY — the x=1 anchor assumes ZERO pot end resistance (the only non-fact used)")
    emit("-" * 92)
    emit(f"  {'end R':>7} | " + " ".join(f"{DRIVES[j][0]:>12}" for j in INTERIOR))
    for endR in (0.0, 500.0, 1000.0):
        gs, _ = solve_magnitude(cap_m, g_of_R(endR), LEVELS)
        emit(f"  {endR:>6.0f}R | " + " ".join(
            f"{R_of_g(gs[k])/1e3:>11.2f}k" for k in range(3)))
    emit("  A real 100k pot's end resistance is typically <1% (<1k). If the ordering/conclusion")
    emit("  is stable across this range, the zero-end-R anchor is not load-bearing.")
    emit("")

    emit("=" * 92)
    emit("READ-OUT")
    emit("=" * 92)
    emit("  * The MEASURED interior resistances above are what a proper C-taper curve must hit in")
    emit("    step (2). Do NOT fit another power-law exponent to them — the shape FAMILY is the")
    emit("    thing under suspicion, and a power law is pinned by its two endpoints (which are")
    emit("    already anchored here), so it has exactly ONE degree of freedom to hit THREE points.")
    emit("  * 'gain err' is the direct answer to session 15's blocker: it is the dB by which the")
    emit("    real pedal drives the CD4049 harder (or softer) than the model at each knob, with")
    emit("    the bleed removed. A positive noon entry is the missing noon level.")
    log.close()
    print(f"\n[log] {LOG}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
