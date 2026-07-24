#!/usr/bin/env python3.11
"""Phase-7 step 3 — fit the CD4049 clipper + J201 shaper to HARMONIC-TO-HARMONIC ratios.

** THE OBJECTIVE (rewritten 2026-07-23, session 10 — the step-3 fix). **
Earlier this fit scored harmonics re the FUNDAMENTAL (H2/H1, THD, ...). That premise —
"harmonic RATIOS are level-independent" — is FALSE in this chain and invalidated THREE fits
(full write-up: docs/phase7-calibration-handover.md, "THE EVEN-HARMONIC LADDER WAS AN
ARTEFACT"). At BLEND = max-OD the output is alpha(B)*OD + beta(B)*CLEAN, and the clean tap
carries NO harmonics, so every measured harmonic-re-FUNDAMENTAL ratio is diluted by the
OD-vs-clean LEVEL — which is exactly what the fit params move. The fitter therefore bought
harmonic score with level: it drove jfetGm 25x below nominal, cranked `a` to claw H2 back,
hit the monotonicity gate, and the bump's saturation manufactured the excess H4 that was
misread as a structural flaw. The shaper shape is FINE; do NOT reshape it.

THE FIX: score harmonic-TO-HARMONIC ratios — Hn - H2 in dB (n = 3,4,5). Every harmonic at
the output is alpha(B)*OD_n (bleed-free, since CLEAN has no harmonics), so a ratio of two
harmonics cancels alpha EXACTLY. That makes the objective immune to the BLEND clean bleed AND
to makeup, levelTaperExp and masterTaperExp — genuinely level-independent, which the old
objective only ever CLAIMED to be. (Hn - H2 = (Hn re H1) - (H2 re H1); H1 cancels
identically, which is why we can build it from the existing re-fundamental profile without
ever touching the contaminated fundamental.) The H2-re-fundamental and THD-re-fundamental
terms are DROPPED — both divide by the contaminated output fundamental.

jfetGm is now HELD at 0.10 mS (step 2, analysis/reanchor_gm.py: bleed-aware re-anchor gave
gm ~= 0.10 mS, band 0.09-0.15, corroborating 0.090 bleed-FREE). A harmonic-only objective
must NOT be allowed to vote on gm — that was the whole failure mode. levelTaperExp is held at
the step-1 measured 2.25 (irrelevant to the ratios, since alpha cancels, but keeps the render
faithful); jfetRo/jfetRq2 held at nominal (not identifiable from this data, session 4).

Fit set: jfetSatPos(s), jfetSatNeg(a), jfetCeilPos/Neg, jfetExpandBeta, clipA0, clipSatLo/Hi.
(driveTaperExp was fit in session 10 but is now HELD at 2.5 from the step-4 LEVEL validation —
see HELD below.) ** jfetExpandBeta (branch B, session 15) is the new EXPANSIVE-cubic H3 lever;
its §3j gate PASSED before this fit ran — see FIT_KEYS. The objective is now phase-aware: a
drive-min ψ3-at-1kHz term (PHASE_TONE/PHASE_W) pins the H3 SIGN so it can't drift compressive. **
Sanity anchor: at s = 0.3, nominal ceilings/clipper, a ~= 4 lands drive-min H2 within ~0.5 dB
of the capture at either gm candidate — so expect a fitted `a` in SINGLE DIGITS, not the
5.5-20 the rejected re-fundamental runs produced.

Acceptance (step 4) requires corroboration the objective could NOT see (checks printed below):
the square-law identity 2*a*jfetCeilNeg ~= 1 (deliberately NOT constrained here), clipA0
inside circuit.md's 20-30, and NO parameter resting on a bound. Commit nothing to the DSP
until acceptance passes. Also re-run at gm in {0.09, 0.12, 0.15} mS (--gm-scan): the ratios
should be nearly gm-insensitive; a large swing would mean the objective is still coupling to
level somewhere.

Speed trick: the capture targets are precomputed CONSTANTS (measured once from the real captures),
so each optimiser eval only renders a SHORT synthetic 220 Hz tone through the plug at each drive
setting — ~20x faster than rendering the full 84 s test signal.

Run: /opt/homebrew/bin/python3.11 analysis/fit_nonlinear.py            (the fit)
     /opt/homebrew/bin/python3.11 analysis/fit_nonlinear.py --gm-scan  (gm sensitivity of a point)
"""
import sys, os, subprocess, numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
import phase_harmonics as PH   # reuse its LS complex-harmonic extractor (§3t.6 step 3)
from captures import parse_capture, render_args, load_capture, RENDER_BIN
from scipy.io import wavfile
from scipy.optimize import minimize

FS = 48000
F0 = 220.0
CAP = "analysis/captures"
# jfetSatPos = square-law knee `s`; jfetSatNeg = even/H2 strength `a` (JfetStage reshape 2026-07-22).
# The harmonic-vs-drive SLOPE (how fast the clipper ramps across the knob) is set by the drive taper
# AND coupled to the clipper/JFET gains. Session 10 fit driveTaperExp jointly here; session 11 pins
# it to the step-4 level measurement (2.5) and lets ONLY the clipper/JFET shape re-absorb — the
# taper shape is now data (a level capture), not a free harmonic-fit param.
#
# ** jfetGm is NOW HELD, not fit (step-3 change, session 10). ** A harmonic-only objective must
# not vote on gm — that is exactly the failure mode that produced three uncommittable fits. gm
# is anchored bleed-free at 0.10 mS by analysis/reanchor_gm.py (step 2); the harmonic-to-harmonic
# ratios are (by construction) nearly gm-insensitive, so holding it costs the fit nothing and
# removes the level<->harmonic coupling. jfetRo/jfetRq2 are not identifiable from this data
# (session 4) and levelTaperExp cancels in the ratios — all HELD, emitted explicitly so a render
# is never at the mercy of the binary's defaults.
#
# ** jfetCeilPos/jfetCeilNeg — the J201 drain-current ceiling. ** It fixes the structural gap
# the step-2 runs exposed (an unbounded shaper whose H2 grew +21.9 dB across the sweep vs the
# capture's +6). Deliberately NOT constrained to the square law here so 2*a*ceilNeg ~= 1 stays
# an INDEPENDENT acceptance check (step 4), not an assumption baked into the fit.
# ** jfetExpandBeta — the branch-B EXPANSIVE cubic (session 15, 2026-07-23). ** The J201's
# drive-min H3 was proven EXPANSIVE-signed (in-phase with the clipper) — no compressive shape
# can make it (session 14 pivot + §3t.5 phase measurement). The core is now
# w*(1+c*w^2)/(1+(w/L)^2)^1.5, c=beta+1.5/L^2, small-signal w+beta*w^3; beta>0 IS the expansive
# H3. It is the PRIMARY H3 lever now (the compressive ceilings jfetCeilPos/Neg only make the H2
# asymmetry + bound the loud swing). Its §3j gate PASSED (analysis/expandbeta_gate.py,
# analysis/fit_logs/step5_expandbeta_gate.log): drive-min H3-H2 rises monotonically to the
# capture's -23.2 at beta~1.8 with the core-H3 IN-PHASE with the clipper, no anti-phase null.
# ** clipK — the CD4049 VTC knee hardness (session 11, ADDED to the fit in session 15). ** Its
# per-side sigmoid is u/(1+u^k)^(1/k) (Clipper.h vtc()). Session 11 identified it as the lever for
# the drive-NOON H3-H2 shortfall, but its §3j pivot FAILED in session 12 — because the JFET
# ceiling's ANTI-PHASE H3 was masking the clipper's noon ramp. With the branch-B JFET now IN-PHASE
# (session 15), the pivot signature RETURNS: at the fitted JFET point, softening clipK 2.0->1.0
# raises noon H3-H2 -17.3 -> -9.1 (toward capture -10.6) while drive-min stays put (analysis probe,
# session 15) — the discriminating check the session-11 plan required before trusting clipK. The
# clipper has NO ADAA (oversampling carries its antialiasing — dsp-validator session 15), so any k
# is shippable (the k=2 fast path is only a VTC-eval optimisation, not an ADAA requirement).
FIT_KEYS = ["jfetSatPos", "jfetSatNeg", "jfetCeilPos", "jfetCeilNeg", "jfetExpandBeta",
            "clipA0", "clipSatLo", "clipSatHi", "clipK"]
NOMINAL  = [0.3, 4.0, 1.0, 0.5, 1.8, 25.0, 3.15, 3.85, 1.5]
# Held fixed at every eval. jfetGm = 0.10 mS (step-2 re-anchor, band 0.09-0.15); levelTaperExp =
# 2.25 (step-1 measured); jfetRo/jfetRq2 nominal (inert / unidentifiable). --gm-scan overrides
# jfetGm to probe the ratios' gm-sensitivity at a fixed parameter point.
#
# ** driveTaperExp is NOW HELD at 2.5 (step-4 JOINT RE-FIT, session 11). ** Session 10's fit let
# driveTaperExp float and it landed at 5.45 — but the step-4 matched-pair LEVEL validation
# (analysis/drive_taper_validate.py, analysis/fit_logs/step4_drive_taper.log) REJECTED that: the
# compression-free small-signal DRIVE gain at the linear interior knob points (9:30, noon) measures
# p = 2.50 (clean taper err 0.18 dB), while p = 5.45 runs noon +8.5 dB too hot (err 6.44 dB). The
# 5.45 was the harmonic objective buying its targets with taper (more gain into the clipper) instead
# of the real taper — exactly the coupling dsp.md's "fit the taper SHAPE against a matched-pair
# capture" guards against. So the taper is now ANCHORED to that level measurement and the clipper/
# JFET shape params re-absorb here. (Pinning p shallower under-drives the clipper at high knob, so
# expect clipA0/clipSat to shift to keep the harmonic ratios.)
HELD = {"jfetGm": 0.10e-3, "jfetRo": 200.0e3, "jfetRq2": 1.0e6,
        "levelTaperExp": 2.25, "driveTaperExp": 2.5}
# BOUNDS on the fitted params. The shaper's argument is the effective vgs (REAL gate volts):
#   jfetSatPos knee `s` in gate volts — order |Vp| (0.3-1.5 V for a J201), room either side.
#   jfetSatNeg even strength `a` (1/V) = 1/Vov. The real constraint is a PRODUCT/COUPLING with
#              s and the ceilings, not a box — enforced by monotonic() below.
#   jfetCeilPos load-line ceiling, gate-volt equivalent.
#   jfetCeilNeg cutoff ceiling = Vov/2. Physically ties to `a` as 1/(2a); left free so that
#              identity stays an independent check on the result rather than an assumption.
#   clipA0     CD4049 open-loop gain; circuit.md says 20-30. Lower bound 3 so a pin on it is
#              still diagnostic (the step-2 runs pinned it at 3 when starved).
#   clipSatLo/Hi per-side clip ceilings (V); their sum tests against the ~7 V R19-dropped rail.
# (driveTaperExp is no longer fit — HELD at 2.5 from the step-4 level validation; see HELD above.)
#   jfetExpandBeta expansive cubic coefficient (1/V^2). >= 0 for the whole branch (a negative
#              beta is the old compressive regime and would fail the gate again); upper bound
#              generous. Provably monotone for beta >= 0, so no coupling for BOUNDS to express.
#   clipK      CD4049 VTC knee hardness. Lower = softer = raises noon H3 (the session-11 lever).
#              [1.0, 4.0]: k=1 and k=2 are the closed-form anchors, and the clipper has no ADAA so
#              any k in-between ships fine; k<1 makes the sigmoid degenerate near the origin.
# ** PHYSICAL bounds (session-15 constrained refit). ** The unconstrained clipK refit found a
# DEGENERATE corner — clipK pinned at 1.0, clipSat sum 1.58 V (vs ~7 V rail), 2*a*ceilNeg 12.7,
# beta 5.2 — the fitter forcing a steep mid-ramp + flat top by dropping the clip ceiling
# unphysically (the pre-existing "too hot into the clipper" blocker, NOT a branch-B failure —
# the JFET H3 phase is correct, ψ3 err 8.6 deg). Constrain the clipper to its PHYSICAL envelope
# so the fit reports the best branch-B result the real clipper can reach, and any residual noon
# gap is honestly the clipper-level blocker, not a hidden cheat:
#   clipSatLo/Hi each [1.5, 4.0] (sum 3-8 V — R19-dropped rail, circuit.md), clipK [1.2, 3.0]
#   (off the soft floor), beta [0, 4] (the gate's drive-min -23.2 crossing is ~1.8, not 5+).
BOUNDS   = [(0.05, 5.0), (0.0, 10.0), (0.05, 20.0), (0.05, 10.0), (0.0, 4.0),
            (3, 30), (1.5, 4.0), (1.5, 4.0), (1.2, 3.0)]
# drive capture -> label
DRIVE_CAPS = [
    ("drive-0700_base-od.wav", "min"),
    ("drive-0930_base-od.wav", "9:30"),
    ("ref-od.wav",             "noon"),
    ("drive-1430_base-od.wav", "2:30"),
    ("drive-1700_base-od.wav", "max"),
]
# Harmonic-TO-HARMONIC ratio terms (dB): Hn - H2. Fundamental cancels (both are re-fund) and
# alpha (BLEND bleed / makeup / tapers) cancels EXACTLY because every output harmonic is
# alpha*OD_n. H3-H2 is the primary discriminator (clipper-odd H3 vs J201-even H2); H4/H5 sit
# 20-40 dB lower and are noisier -> down-weighted.
RATIO_W = {("H3", "H2"): 1.0, ("H4", "H2"): 0.5, ("H5", "H2"): 0.3}

SHORT_IN = "/tmp/fit_tone220.wav"

# ---- Phase-aware ψ3 target (branch B, §3t.6 step 3) -----------------------------------------
# The whole session-7-14 saga was amplitude fits that hid an anti-phase cancellation. Now that
# beta makes the JFET H3 EXPANSIVE, the fit must also PIN the phase so it can't drift back.
# ψ3 = φ3 - 3φ1 is shift-invariant (phase_harmonics.py), so it is comparable model-vs-capture
# without alignment. Measured at DRIVE-MIN (the JFET-dominated point) at 1000 Hz — the one
# CLEAN, conclusive tone (§3t.5: capSNR 47, notch-free). 220/440 are DOWN-WEIGHTED to zero here:
# their H3 (660/1320 Hz) sits near the bridged-T notch whose phase the linear model gets wrong
# (§3t.1/§3t.3), so a ψ3 mismatch there is a LINEAR-phase artefact, not the nonlinear sign. The
# weight is deliberately MODEST: the magnitude harmonic-to-harmonic ramp already forces the
# in-phase solution (an anti-phase beta gives a null, not a monotone ramp — gate Part A), so
# phase is corroboration, not the primary driver; a large weight would let the ~18 deg
# irreducible linear-phase residual at 3 kHz distort beta.
PHASE_TONE = 1000.0
PHASE_IN = "/tmp/fit_tone1k.wav"
PHASE_W = 0.05   # per (deg^2); 18 deg residual -> ~16 cost units, ~1 magnitude-ratio term
DRIVE_MIN_CAP = "drive-0700_base-od.wav"


def _harm(seg, nmax=6):
    w = np.hanning(len(seg)); X = np.abs(np.fft.rfft(seg * w)); frq = np.fft.rfftfreq(len(seg), 1 / FS)
    def amp(f):
        k = np.argmin(np.abs(frq - f)); return X[max(0, k - 3):k + 4].max()
    h = [amp(F0 * n) for n in range(1, nmax + 1)]
    thd = np.sqrt(sum(a * a for a in h[1:])) / (h[0] + 1e-20)
    return h, thd


def _profile(seg):
    """{H2..H5 dB re fundamental, THD dB} from a steady 220 Hz segment (edges trimmed)."""
    m = len(seg) // 6
    h, thd = _harm(seg[m:-m])
    d = {f"H{i+1}": 20 * np.log10(h[i] / h[0] + 1e-20) for i in range(1, 5)}
    d["THD"] = 20 * np.log10(thd + 1e-20)
    return d


def _short_tone(path, f0):
    n = int(1.2 * FS)
    t = np.arange(n) / FS
    x = (10 ** (-14 / 20)) * np.sin(2 * np.pi * f0 * t)
    # short fades so the render's smoothers settle before the measured window
    k = int(0.02 * FS); env = np.ones(n); env[:k] = np.linspace(0, 1, k); env[-k:] = np.linspace(1, 0, k)
    wavfile.write(path, FS, (x * env).astype(np.float32))


def make_short_input():
    _short_tone(SHORT_IN, F0)
    _short_tone(PHASE_IN, PHASE_TONE)   # 1 kHz for the drive-min ψ3 phase term


def capture_targets():
    tg = {}
    for cap, lbl in DRIVE_CAPS:
        c = load_capture(f"{CAP}/{cap}")
        tg[lbl] = _profile(A.seg_of(c, "tone_220"))
    return tg


def capture_phase_target():
    """Capture drive-min ψ3 (deg) at PHASE_TONE — the phase the fit's ψ3 must match. Measured
    with phase_harmonics' shift-invariant LS extractor on the real drive-min capture."""
    c = load_capture(f"{CAP}/{DRIVE_MIN_CAP}")
    seg = PH.steady_window(A.seg_of(c, f"tone_{PHASE_TONE:g}"))
    H, _, _ = PH.fit_harmonics(seg, PHASE_TONE)
    return PH.rel_phase(H)[3]


def render_phase(params):
    """Render the short 1 kHz tone at DRIVE-MIN through the plug; return model ψ3 (deg)."""
    extra = []
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    for k, v in zip(FIT_KEYS, params):
        extra += ["--fit", f"{k}={v}"]
    parsed = parse_capture(DRIVE_MIN_CAP)
    o = "/tmp/fit_phase1k.wav"
    subprocess.run([RENDER_BIN, PHASE_IN, o, "--os", "8"] + render_args(parsed, extra),
                   check=True, capture_output=True)
    r = A.load(o)
    seg = r[int(0.5 * FS):int(1.15 * FS)]
    H, _, _ = PH.fit_harmonics(seg, PHASE_TONE)
    return PH.rel_phase(H)[3]


def render_profiles(params):
    """Render the short tone through the plug at each drive setting; return {label: profile}."""
    extra = []
    for k, v in HELD.items():
        extra += ["--fit", f"{k}={v:.9g}"]
    for k, v in zip(FIT_KEYS, params):
        extra += ["--fit", f"{k}={v}"]
    out = {}
    for cap, lbl in DRIVE_CAPS:
        parsed = parse_capture(cap)
        o = f"/tmp/fit_{lbl.replace(':','')}.wav"
        subprocess.run([RENDER_BIN, SHORT_IN, o, "--os", "8"] + render_args(parsed, extra),
                       check=True, capture_output=True)
        r = A.load(o)
        # steady window: last ~0.6 s (after smoother settle), trimmed
        seg = r[int(0.5 * FS):int(1.15 * FS)]
        out[lbl] = _profile(seg)
    return out


# ---- Monotonicity feasibility gate -----------------------------------------------
# A fold-back (negative slope) inside the signal range is unphysical AND scores
# spuriously well on H2, so it must be excluded explicitly — the bounds cannot do it,
# because the constraint is a coupling between parameters, not a box. This is not
# hypothetical: the 2026-07-22 run-2 best point was exactly such a fold-back.
#
# ** The gate is a NUMERIC SCAN, not a closed-form product bound. ** With the session-15
# branch-B expansive-then-bounded core (JfetStage.h) the shipped map is
#     g(w)  = T(w) + (a*s^2/2)*tanh^2(w/s),  L = ceilPos (w>=0)/ceilNeg (w<0)
#     T(w)  = w*(1+c*w^2)/(1+(w/L)^2)^1.5,   c = beta + 1.5/L^2
#     T'(w) = L^3*(L^2 + w^2*(3*L^2*beta+2.5)) / (sqrt(L^2+w^2)*(L^2+w^2)^2)
#     g'(w) = T'(w) + a*s*tanh(w/s)*sech^2(w/s)
# The CORE is now PROVABLY monotone for beta >= 0 (T' numerator = L^2 + w^2*(3*L^2*beta+2.5)
# is a sum of two strictly positive terms — see JfetStage.h), so unlike the session-14
# sigmoid there is no s/a/L/beta coupling for the core to track. The only closed fold-back
# bound is the even bump's own, |a|*s < 3*sqrt(3)/2 = 2.598 (max|tanh*sech^2| = 2/(3*sqrt(3))).
# The numeric scan still runs on the SUMMED g'(w) per the standing verify rule (an analytic
# derivation has been wrong here before — memory: verify-extremum-derived-bounds). For
# beta < -2.5/(3L^2) the core folds back, but this branch holds beta >= 0.
#
# NOTE this is a REPLICA of JfetStage::coreLimit()'s derivative. The C++ side is the
# source of truth (JfetStageTest finite-differences the shipped map); if the shaper
# changes shape again, this must change with it.
# A saturating map's slope legitimately decays to zero far out in the tail, so the
# test is "never NEGATIVE", not "always positive".
_W = np.concatenate([np.linspace(-60, 60, 24001), np.linspace(-3, 3, 6001)])


def min_slope(s, a, cp, cn, beta=0.0):
    L = np.where(_W >= 0.0, cp, cn)
    L2 = L * L
    w2 = _W * _W
    with np.errstate(over="ignore", invalid="ignore"):
        num = L2 * L * (L2 + w2 * (3.0 * L2 * beta + 2.5))
        den = np.sqrt(L2 + w2) * (L2 + w2) ** 2
        core_slope = np.where(L >= 1.0e6, 1.0, num / den)
    x = np.clip(_W / s, -350, 350)
    bump_slope = a * s * np.tanh(x) / np.cosh(x) ** 2
    return float(np.min(core_slope + bump_slope))


def monotonic(params):
    g = dict(zip(FIT_KEYS, params))
    # jfetExpandBeta is HELD during the pivot gate and only enters FIT_KEYS for the step-3
    # fit; read it from whichever holds it, defaulting to the neutral beta=0.
    beta = g.get("jfetExpandBeta", HELD.get("jfetExpandBeta", 0.0))
    return min_slope(g["jfetSatPos"], g["jfetSatNeg"],
                     g["jfetCeilPos"], g["jfetCeilNeg"], beta) > -1.0e-9


# Set once by main() (capture drive-min ψ3 at PHASE_TONE). None -> phase term OFF (e.g. a
# magnitude-only A/B). Kept module-global so cost()'s signature — and all its callers — are
# unchanged.
PHASE_TARGET = None


def cost(params, targets, verbose=False):
    if not monotonic(params):
        # infeasible: non-monotone (fold-back) waveshaper. Keep the return SHAPE
        # consistent so a verbose call on an infeasible point can't TypeError.
        return (1e6, None) if verbose else 1e6
    try:
        prof = render_profiles(params)
        psi3 = render_phase(params) if PHASE_TARGET is not None else None
    except subprocess.CalledProcessError:
        return (1e6, None) if verbose else 1e6
    total = 0.0
    for lbl in targets:
        for (hi, lo), w in RATIO_W.items():
            e = (prof[lbl][hi] - prof[lbl][lo]) - (targets[lbl][hi] - targets[lbl][lo])
            total += w * e * e
    # Phase-aware term: drive-min ψ3 at 1 kHz (angular error, wrapped). Corroborates the sign;
    # weighted so it can't override the well-conditioned magnitude ratios (see PHASE_W).
    if PHASE_TARGET is not None:
        dphi = PH._deg_err(psi3, PHASE_TARGET)
        total += PHASE_W * dphi * dphi
    if verbose:
        return total, prof
    return total


def gm_scan(params, targets, gms):
    """Re-score ONE parameter point at several held gm values. The harmonic-to-harmonic ratios
    should be nearly gm-insensitive; a large cost swing means the objective still couples to
    level somewhere. Restores HELD['jfetGm'] on exit."""
    saved = HELD["jfetGm"]
    print("\ngm sensitivity of the fitted point (ratios should be ~flat vs gm):")
    print(f"  {'gm(mS)':>7} | {'cost':>7} | " + " | ".join(f"{lbl} H3-H2/H4-H2" for lbl in targets))
    try:
        for gm in gms:
            HELD["jfetGm"] = gm
            c, prof = cost(params, targets, verbose=True)
            cells = []
            for lbl in targets:
                p = prof[lbl]
                cells.append(f"{p['H3']-p['H2']:+5.1f}/{p['H4']-p['H2']:+5.1f}")
            print(f"  {gm*1e3:>7.3f} | {c:>7.1f} | " + " | ".join(cells))
    finally:
        HELD["jfetGm"] = saved


def main():
    global PHASE_TARGET
    make_short_input()
    targets = capture_targets()
    PHASE_TARGET = capture_phase_target()   # capture drive-min ψ3 at 1 kHz (branch-B phase term)
    print("Capture targets (tone_220): harmonic-to-harmonic ratios (dB) are the objective;")
    print("H2 re-fund shown for reference only (NOT fit — it is bleed-contaminated).")
    print(f"  {'drive':5s}  {'H3-H2':>7} {'H4-H2':>7} {'H5-H2':>7}   {'(H2reF)':>8}")
    for lbl, p in targets.items():
        print(f"  {lbl:5s}  {p['H3']-p['H2']:>7.1f} {p['H4']-p['H2']:>7.1f} {p['H5']-p['H2']:>7.1f}   "
              f"{p['H2']:>8.1f}")
    print(f"Phase target: drive-min ψ3 @ {PHASE_TONE:g} Hz = {PHASE_TARGET:+.1f} deg "
          f"(weight {PHASE_W}/deg^2; 220/440 down-weighted to 0 — bridged-T notch)")

    # --gm-scan: probe gm-sensitivity of a point WITHOUT re-fitting. Point comes from --start=
    # if given, else NOMINAL. This is the step-3 gm-insensitivity check. Phase OFF here (the
    # ratios are the gm-sensitivity object; phase is ~gm-flat and would just add render cost).
    if "--gm-scan" in sys.argv:
        PHASE_TARGET = None
        pt = NOMINAL
        for arg in sys.argv[1:]:
            if arg.startswith("--start="):
                pt = [float(v) for v in arg.split("=", 1)[1].split(",")]
        gm_scan(pt, targets, [0.09e-3, 0.10e-3, 0.12e-3, 0.15e-3])
        return

    c0 = cost(NOMINAL, targets)
    print(f"\nNominal cost = {c0:.1f}")

    # Nelder-Mead from nominal, then a light restart.
    # `--start a,b,c,...` refines from ONE explicit point instead (used to re-run a previous
    # best under WIDENED bounds — a param that came back resting on a bound must be re-fit,
    # not committed).
    best = None
    # Starts (gm AND driveTaperExp HELD now): [s, a, cp, cn, clipA0, clipSatLo, clipSatHi].
    # All feasible (min_slope > 0). With the taper PINNED at 2.5 the multi-modal-in-driveExp basin
    # split of session 10 is gone; these three just spread the clipper/JFET start so the re-absorb
    # doesn't sit in a local min. Start 1 = the session-10 shape at its fitted knee/ceilings, start 2
    # a tighter knee + lower ceiling, start 3 = nominal.
    # [s, a, cp, cn, BETA, clipA0, clipSatLo, clipSatHi, clipK]. Start 1 = the session-15
    # beta-only fit (clipK 2.0) — the refit adds clipK freedom from there; starts 2/3 seed a
    # SOFTER clipK (1.3/1.5) with a HIGHER rail (clipSat sum ~7 V) so the optimiser can find the
    # "soft knee + late saturation" basin that raises noon without overshooting 2:30/max.
    starts = [
        [0.33, 1.69, 1.43, 0.49, 1.8, 25, 3.15, 3.15, 1.5],
        [0.30, 1.8, 1.4, 0.5, 1.6, 28, 3.5, 3.5, 1.3],
        [0.28, 2.5, 1.0, 0.45, 2.0, 22, 2.5, 3.0, 2.0],
    ]
    for arg in sys.argv[1:]:
        if arg.startswith("--start="):
            starts = [[float(v) for v in arg.split("=", 1)[1].split(",")]]
    for start in starts:
        res = minimize(cost, start, args=(targets,), method="Nelder-Mead",
                       bounds=BOUNDS, options=dict(maxiter=400, xatol=0.02, fatol=0.3))
        if best is None or res.fun < best.fun:
            best = res
        print(f"  start {[round(s,1) for s in start]} -> cost {res.fun:.1f}")

    print(f"\nBest cost = {best.fun:.1f}  (nominal {c0:.1f})")
    print("Fitted params:")
    for k, v, nom in zip(FIT_KEYS, best.x, NOMINAL):
        print(f"  {k:12s} {v:12.5g}   (nominal {nom:g})")
    print(f"  held: " + ", ".join(f"{k}={v:g}" for k, v in HELD.items()))

    # ---- Acceptance diagnostics (step 4) ----------------------------------------
    # Corroboration the harmonic-to-harmonic objective could NOT see. Every prior run was
    # rejected by exactly these, so print them rather than re-deriving by hand.
    g = dict(zip(FIT_KEYS, best.x))
    print("\nAcceptance checks (phase7-calibration-handover.md, step 4):")
    print(f"  |a|*s          = {abs(g['jfetSatNeg']) * g['jfetSatPos']:.4f}   "
          f"(monotonicity coupling; a fitted a should be single-digit)")
    print(f"  min slope      = {min_slope(g['jfetSatPos'], g['jfetSatNeg'], g['jfetCeilPos'], g['jfetCeilNeg'], g.get('jfetExpandBeta', HELD.get('jfetExpandBeta', 0.0))):+.3e}   "
          f"(>= 0; a fold-back is infeasible)")
    a0ok = "" if 20.0 <= g["clipA0"] <= 30.0 else " ** OUTSIDE circuit.md's 20-30 **"
    print(f"  clipA0         = {g['clipA0']:.3f}   (circuit.md says 20-30){a0ok}")
    print(f"  clipSatLo+Hi   = {g['clipSatLo'] + g['clipSatHi']:.3f} V   (R19-dropped rail ~7 V)")
    print(f"  2*a*ceilNeg    = {2 * g['jfetSatNeg'] * g['jfetCeilNeg']:.3f}   "
          f"(square law says ~1.0 — NOT constrained in the fit, so this is a real check)")
    print(f"  ceilNeg / s    = {g['jfetCeilNeg'] / g['jfetSatPos']:.2f}   "
          f"(monotonicity needs >~ 1; resting AT 1 means the ceiling is on a constraint)")
    print(f"  jfetExpandBeta = {g['jfetExpandBeta']:.3f}   "
          f"(EXPANSIVE cubic; must be > 0 — a <= 0 is the compressive regime the gate rejects)")
    beta_ok = " ** beta <= 0: NOT expansive, the gate premise is violated **" if g['jfetExpandBeta'] <= 0.0 else ""
    if beta_ok:
        print(f"    {beta_ok}")
    if PHASE_TARGET is not None:
        psi3 = render_phase(best.x)
        dphi = PH._deg_err(psi3, PHASE_TARGET)
        print(f"  ψ3 @ {PHASE_TONE:g}Hz    = model {psi3:+.1f} vs capture {PHASE_TARGET:+.1f} deg "
              f"(|err| {abs(dphi):.1f}; small = JFET H3 in-phase, the branch-B claim)")
    print(f"  held jfetGm    = {HELD['jfetGm'] * 1e3:.3f} mS   "
          f"(step-2 re-anchor; --gm-scan checks ratio sensitivity, band 0.09-0.15)")
    # 1% of the bound, not 0.1%: Nelder-Mead stops NEAR a bound it is pushing against
    # rather than exactly on it (the 2026-07-22 ceiling run returned driveTaperExp
    # 2.9938 against a ceiling of 3.0 — 0.2% off, and a 0.1% test missed it).
    for k, v, (lo, hi) in zip(FIT_KEYS, best.x, BOUNDS):
        if abs(v - lo) < 1e-2 * max(abs(lo), 1e-9) or abs(v - hi) < 1e-2 * abs(hi):
            print(f"  ** {k} is RESTING ON ITS BOUND ({v:g} in [{lo:g}, {hi:g}]) — the optimum is "
                  f"outside the box, so this value is a property of the box, not the pedal. **")

    _, prof = cost(best.x, targets, verbose=True)
    if prof is None:
        print("\n** every start was INFEASIBLE (fold-back shaper) — no profile **")
        return
    print("\nFITTED plug vs capture (tone_220): harmonic-to-harmonic ratios c/p (the objective),")
    print("plus H2 re-fund c/p for reference (NOT fit — bleed-contaminated).")
    print(f"{'drive':6s} | {'H3-H2 c/p':>13s} | {'H4-H2 c/p':>13s} | {'H5-H2 c/p':>13s} | {'(H2reF) c/p':>13s}")
    for lbl in targets:
        t, p = targets[lbl], prof[lbl]
        print(f"{lbl:6s} | {t['H3']-t['H2']:5.1f}/{p['H3']-p['H2']:5.1f} | "
              f"{t['H4']-t['H2']:5.1f}/{p['H4']-p['H2']:5.1f} | "
              f"{t['H5']-t['H2']:5.1f}/{p['H5']-p['H2']:5.1f} | "
              f"{t['H2']:5.1f}/{p['H2']:5.1f}")

    print("\nStep-4 gm-sensitivity of the fitted point (should be ~flat):")
    gm_scan(best.x, targets, [0.09e-3, 0.12e-3, 0.15e-3])


if __name__ == "__main__":
    main()
