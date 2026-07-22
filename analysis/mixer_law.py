#!/usr/bin/env python3.11
"""Phase-7 step 2 PREREQUISITE — measure the real BLEND/LEVEL mixer law from existing captures.

Why this exists
---------------
Three step-2 nonlinear fits were rejected, and session 7 (2026-07-23) found the common cause:
`fit_nonlinear.py`'s objective is NOT level-independent, because at BLEND = max-OD the output
still contains a harmonic-free CLEAN component (LevelBlend's KCL solution keeps `cleanIn` in
`vw`). Every `jfetGm` estimate on record (0.551 / 0.090 / 0.0274 mS) is therefore really a
measurement of the OD/clean MIX RATIO, and inherits any error in the BLEND model. So the mixer
must be settled BEFORE anything downstream. Full rationale:
docs/phase7-calibration-handover.md, "THE PATH FORWARD FOR THE J201".

Topology (VERIFIED at pixel zoom, session 8, 2026-07-23 — primary p.4 at 600 dpi)
--------------------------------------------------------------------------------
    VR2 LEVEL: pin3 = IC4_A out (OD), pin1 = VD (direct, no series R), wiper -> VR1 pin3
    VR1 BLEND: pin3 = LEVEL wiper, pin1 = clean rail straight off IC1_A pin1,
               wiper -> IC5_A(+) (unity buffer, high-Z => wiper UNLOADED)
Both long rails were scanned pixel-by-pixel end to end: bare wire, no series element, no
junction dot, no shunt to VD/GND anywhere. So `LevelBlend.h` is a faithful implementation and
the clean bleed at full-CW OD is a real property of the drawn circuit, not a modelling error.

Closed form that falls out (and that this script tests). With the wiper unloaded, at BLEND
full-CW the clean-to-OD AMPLITUDE ratio is exactly `(1 - L)`, independent of the pot value:

    alpha(L) = L / (1 + L(1-L))        <- OD coefficient   at BLEND = max-OD
    beta(L)  = L(1-L) / (1 + L(1-L))   <- clean coefficient at BLEND = max-OD
    beta/alpha = (1 - L)

⚠ This CORRECTS the handover's claim that the LEVEL sweep is an independent route "since LEVEL
moves the OD path only". It does not: LEVEL moves the clean bleed too, by exactly (1-L). That
makes the LEVEL sweep a SHARPER test rather than a useless one — the law has no free parameter
left except the taper L(knob), which this script measures bleed-free.

The lever that makes this measurable with NO new captures
--------------------------------------------------------
The clean tap is linear and harmonic-free (IC1_A's output, pre-JFET), and everything after
BLEND (C21, EQ, MASTER, output buffer) is linear too. So at the OUTPUT, for one input tone:

    H1  =  alpha * OD_1  +  beta * CLEAN_1      <- CONTAMINATED by the clean bleed
    Hn  =  alpha * OD_n            (n >= 2)     <- BLEED-FREE. Pure OD path.

OD_n and CLEAN_1 are FIXED across a BLEND or LEVEL sweep (nothing upstream of the mixer moves),
which is what makes the sweeps solvable.

  BLEND route (LEVEL fixed at noon). alpha(B) = B*alpha(L), beta(B) = (1-B) + B*beta(L), both
  LINEAR IN THE KNOB (BLEND is a linear-taper pot), so EVERY harmonic must be an affine function
  of the knob with ZERO free parameters. Fitted as a COMPLEX regression Hn(B) = F_n + B*G_n:
  the intercept F_n is the harmonic FLOOR (capture chain + the clean path's own residual
  nonlinearity), which has to be modelled or it biases the low-blend points badly.

  LEVEL route (BLEND fixed at max-OD). |Hn| is bleed-free, so inverting alpha(L) from the
  measured harmonic ratio measures L at each knob position DIRECTLY -> the LEVEL taper, with no
  reference to the fundamental. Then within each single capture (no cross-file phase risk):

      Y(L) = H1/H2 = OD_1/OD_2 + (1-L) * CLEAN_1/OD_2      <- AFFINE in (1-L)

  and the fitted slope/intercept gives CLEAN_1/OD_1 — the clean-vs-OD ratio at the mixer inputs
  — free of every unknown scale (makeup, masterTaperExp, kInputRef, interface gain), because
  both sides are ratios measured inside one file.

⚠ SCOPE: these are DRIVE = noon captures. The COEFFICIENT law (1-L) is drive-independent (it is
pure resistive divider arithmetic), and so is the taper. CLEAN_1/OD_1 is NOT — it is an
operating-point measurement at drive-noon. The J201 re-anchor needs OD_1 at DRIVE-MIN; use the
law measured here plus the drive-min captures for that.

Run: /opt/homebrew/bin/python3.11 analysis/mixer_law.py
"""
import os
import sys
import warnings

import numpy as np

warnings.filterwarnings("ignore")
sys.path.insert(0, os.path.dirname(__file__))
import analyze as A
from captures import load_capture

CAP = "analysis/captures"
FS = A.FS

# The mixer is resistive, so its law is frequency-independent: a result that only holds at one
# tone is a measurement artefact, not the mixer. 220 Hz is the tone fit_nonlinear.py profiles.
TONES = [("tone_110", 110.0), ("tone_220", 220.0), ("tone_440", 440.0)]

# ref-od is the shared corner of both sweeps: BLEND max-OD AND LEVEL noon (captures.py::_REF_OD).
BLEND_CAPS = [(0.00, "blend-0700_base-od.wav"), (0.25, "blend-0930_base-od.wav"),
              (0.50, "blend-1200_base-od.wav"), (0.75, "blend-1430_base-od.wav"),
              (1.00, "ref-od.wav")]
LEVEL_CAPS = [(0.00, "level-0700_base-od.wav"), (0.25, "level-0930_base-od.wav"),
              (0.50, "ref-od.wav"), (0.75, "level-1430_base-od.wav"),
              (1.00, "level-1700_base-od.wav")]

# ⚠ EXCLUSIONS — each needs a reason that is independent of the model being tested, or this
# degenerates into discarding whatever disagrees.
#
# level-1430_base-od: RE-CAPTURED 2026-07-23 (session 8) after the original take was found
#   ODD-dominant (H3 -45.4, H5 -52.4, vs H2 -59.9, H4 -83.8) while every other capture in the
#   session is EVEN-dominant — a passive divider cannot create odd harmonics, and the original
#   take's own gain-n12 twin was essentially harmonic-free, 61 dB less H3 for a 9 dB level drop.
#   The new take is even-dominant (H2 -53.4, H3 -64.9 at tone_220) — consistent with the set, so
#   that specific defect is fixed. No longer excluded on THAT basis.
#   ⚠ BUT a SECOND, separate issue is suspected and a round-2 re-capture is in progress as of
#   2026-07-23: this file may have been captured with BLEND left at noon instead of the required
#   max-OD (every level-*.wav file needs BLEND pinned at full-CW per the _REF_OD baseline in
#   captures.py). If so, its alpha/beta mix does not match what level_route()/bleed_from_level_
#   sweep() assume, and that alone explains the taper-shape anomaly this file introduces at
#   knob=0.75 (see docs/phase7-calibration-handover.md 1d/1f) with no real taper irregularity
#   required. DO NOT treat 1d's "taper is not a single power law" conclusion as settled until a
#   confirmed-BLEND=max recapture lands and this script is re-run against it.
# level-0700_base-od: L = 0 is a deep NULL by construction (the wiper sits on VD), so the
#   residual is 40 dB down and whatever leaks through is not the OD path's spectrum. Ratios
#   measured in a null are meaningless. Excluded on principle, not on disagreement.
EXCLUDE = {
    "level-0700_base-od.wav": "L=0 null — residual is 40 dB down, ratios meaningless",
}

LEVEL_TAPER_EXP_NOMINAL = 1.43  # LevelBlend::kLevelTaperExp — INTERIM. This script MEASURES it.


# ---- model (mirrors src/dsp/LevelBlend.h) ------------------------------------------------
def blend_max_coeffs(L):
    """(alpha, beta) at BLEND full-CW, i.e. Vout = alpha*od + beta*clean."""
    if L <= 0.0:
        return 0.0, 0.0
    if L >= 1.0:
        return 1.0, 0.0
    d = 1.0 + L * (1.0 - L)
    return L / d, L * (1.0 - L) / d


def mix_coeffs(L, B):
    """General (alpha, beta) for any LEVEL/BLEND pair."""
    c_od, c_cl = blend_max_coeffs(L)
    if B <= 0.0:
        return 0.0, 1.0
    if B >= 1.0:
        return c_od, c_cl
    return B * c_od, (1.0 - B) + B * c_cl


def alpha_to_L(a):
    """Invert alpha(L) = L/(1+L(1-L)) on [0,1]. Monotone increasing, so bisection is safe."""
    if a <= 0.0:
        return 0.0
    if a >= 1.0:
        return 1.0
    lo, hi = 0.0, 1.0
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if blend_max_coeffs(mid)[0] < a:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


# ---- measurement -------------------------------------------------------------------------
_ORIG = None


def _orig():
    global _ORIG
    if _ORIG is None:
        _ORIG = A.load(A.ORIG)
    return _ORIG


def measure(path, seg_name, f0, nmax=5):
    """Aligned complex harmonic amplitudes + a non-harmonic noise floor for one capture/tone.

    Hann-windowed DFT projection at the EXACT harmonic frequencies: the window's mainlobe is
    ~4/T = 6.7 Hz over the 0.6 s analysis window against >=110 Hz harmonic spacing, so
    inter-harmonic leakage is negligible. Normalised so |X| is a pure sine's amplitude.
    Phase is meaningful across captures only because each is aligned to the same reference
    first — but every conclusion below is drawn from ratios WITHIN one capture, which is
    immune to residual sub-sample alignment error.
    """
    x = load_capture(path)
    orig = _orig()
    assert A.is_full_length(x, orig), f"{path}: truncated capture"
    x, _lag = A.align(x, orig)
    seg = A.seg_of(x, seg_name)
    seg = seg[int(0.15 * FS):len(seg) - int(0.05 * FS)]  # steady middle, skip attack/release

    n = len(seg)
    w = np.hanning(n)
    t = np.arange(n) / FS
    norm = 2.0 / np.sum(w)

    def proj(f):
        return np.sum(seg * w * np.exp(-2j * np.pi * f * t)) * norm

    h = np.array([proj(f0 * k) for k in range(1, nmax + 1)])

    # Broadband noise floor. ⚠ Do NOT estimate this by projecting at half-harmonic frequencies:
    # against a near-pure tone that measures the WINDOW's sidelobe rejection (~-170 dB), not the
    # capture's noise, and every SNR derived from it is fiction. Use the median magnitude of the
    # actual spectrum over bins that are not within +-15 Hz of any harmonic.
    X = np.abs(np.fft.rfft(seg * w)) * norm
    frq = np.fft.rfftfreq(n, 1.0 / FS)
    mask = (frq > 0.5 * f0) & (frq < 12000.0)
    for k in range(1, 40):
        mask &= np.abs(frq - f0 * k) > 15.0
    floor = float(np.median(X[mask])) if mask.any() else 0.0
    return h, floor


def db(x):
    return 20.0 * np.log10(np.abs(x) + 1e-20)


def complex_affine_fit(xs, ys):
    """Least-squares y = c0 + c1*x with complex y, real x. Returns (c0, c1, rms_residual)."""
    M = np.column_stack([np.ones(len(xs)), np.asarray(xs, dtype=float)])
    c, *_ = np.linalg.lstsq(M, np.asarray(ys), rcond=None)
    resid = np.asarray(ys) - M @ c
    return c[0], c[1], float(np.sqrt(np.mean(np.abs(resid) ** 2)))


# ---- routes ------------------------------------------------------------------------------
def bleed_from_blend(F1, G1, L_noon):
    """The BEST-CONDITIONED bleed estimate: 5 BLEND points, all far above the noise floor.

    The BLEND sweep's complex affine fit H1(B) = F1 + B*G1 has, from the mixer law,
        F1 = CLEAN_1                                  (B=0 is exactly the clean tap)
        G1 = alpha_n*OD_1 + (beta_n - 1)*CLEAN_1
    with (alpha_n, beta_n) = blend_max_coeffs(L_noon). So the OD contribution at full-CW OD is

        alpha_n*OD_1 = G1 + (1 - beta_n)*F1

    and the clean-to-OD amplitude ratio actually present in the output at ref-od is

        bleed = beta_n*F1 / (alpha_n*OD_1).

    Summed as PHASORS — the OD and clean paths reach the mixer with different phase, and both
    terms come from one within-sweep fit, so no cross-file phase reference is involved.
    L_noon is the one input from outside (measured bleed-free by the LEVEL route), which is why
    the caller also reports the sensitivity to it.
    """
    a_n, b_n = blend_max_coeffs(L_noon)
    od_term = G1 + (1.0 - b_n) * F1
    if abs(od_term) < 1e-30:
        return float("nan"), float("nan")
    return abs(b_n * F1) / abs(od_term), abs(od_term) / max(a_n, 1e-30)


def blend_route(seg_name, f0):
    """Test the zero-free-parameter prediction that every harmonic is AFFINE in the BLEND knob."""
    print(f"\n--- BLEND sweep (LEVEL at noon) — {seg_name} ---------------------------")
    rows = []
    for knob, fn in BLEND_CAPS:
        if fn in EXCLUDE:
            continue
        h, fl = measure(f"{CAP}/{fn}", seg_name, f0)
        rows.append((knob, h, fl))

    print(f"  {'knob':>5} {'H1 dB':>8} {'H2 dB':>8} {'H3 dB':>8} {'H4 dB':>8} {'floor dB':>9}")
    for knob, h, fl in rows:
        print(f"  {knob:>5.2f} {db(h[0]):>8.2f} {db(h[1]):>8.2f} {db(h[2]):>8.2f} "
              f"{db(h[3]):>8.2f} {db(fl):>9.2f}")

    print(f"\n  Affine-in-knob test  Hn(B) = F_n + B*G_n   (model: EXACT, no free shape)")
    print(f"  {'n':>2} {'|F| dB':>9} {'|G| dB':>9} {'resid dB':>9} {'resid/|G|':>10}  verdict")
    ks = [r[0] for r in rows]
    fits = []
    for n in range(4):
        F, G, res = complex_affine_fit(ks, [r[1][n] for r in rows])
        fits.append((F, G, res))
        rel = res / (abs(G) + 1e-30)
        verdict = "AFFINE" if rel < 0.06 else ("marginal" if rel < 0.15 else "NOT AFFINE")
        print(f"  H{n + 1:<1} {db(F):>9.2f} {db(G):>9.2f} {db(res):>9.2f} {rel:>10.3f}  {verdict}")
    return rows, fits


def level_route(seg_name, f0, harm=1):
    """Measure L(knob) bleed-free, then get CLEAN_1/OD_1 from the affine H1/H2 vs (1-L) law."""
    print(f"\n--- LEVEL sweep (BLEND at max-OD) — {seg_name} -------------------------")
    rows = []
    for knob, fn in LEVEL_CAPS:
        if fn in EXCLUDE:
            print(f"  [skip] {fn}: {EXCLUDE[fn]}")
            continue
        h, fl = measure(f"{CAP}/{fn}", seg_name, f0)
        rows.append((knob, h, fl))

    print(f"  {'knob':>5} {'H1 dB':>8} {'H2 dB':>8} {'H3 dB':>8} {'floor dB':>9} {'H2 SNR':>8}")
    for knob, h, fl in rows:
        print(f"  {knob:>5.2f} {db(h[0]):>8.2f} {db(h[1]):>8.2f} {db(h[2]):>8.2f} "
              f"{db(fl):>9.2f} {db(h[1]) - db(fl):>8.1f}")

    # --- taper, measured from a BLEED-FREE harmonic. alpha(1)=1, so |Hn(L)|/|Hn(1)| IS alpha(L).
    ref = [r for r in rows if r[0] >= 1.0]
    if not ref:
        print("  no LEVEL=max capture — cannot normalise alpha.")
        return None
    hmax = ref[0][1][harm]
    print(f"\n  LEVEL taper from H{harm + 1} (bleed-free): alpha = |Hn|/|Hn(max)|, L = alpha^-1")
    print(f"  {'knob':>5} {'alpha':>8} {'L':>8} {'p=lnL/lnk':>10}   (nominal p = "
          f"{LEVEL_TAPER_EXP_NOMINAL})")
    ps, Ls = [], {}
    for knob, h, _fl in rows:
        a = abs(h[harm]) / abs(hmax)
        L = alpha_to_L(a)
        Ls[knob] = L
        if 0.0 < knob < 1.0 and 0.0 < L < 1.0:
            p = np.log(L) / np.log(knob)
            ps.append(p)
            print(f"  {knob:>5.2f} {a:>8.4f} {L:>8.4f} {p:>10.3f}")
        else:
            print(f"  {knob:>5.2f} {a:>8.4f} {L:>8.4f} {'—':>10}")
    if ps:
        print(f"  => independent p estimates {['%.3f' % v for v in ps]}, "
              f"spread {max(ps) - min(ps):.3f}  (agreement IS the test)")

    # --- the headline: H1/H2 must be AFFINE in (1-L), slope/intercept = CLEAN_1/OD_1.
    usable = [r for r in rows if abs(r[1][harm]) > 4.0 * r[2]]
    if len(usable) < 3:
        print("\n  [bleed] fewer than 3 usable points — not enough to fit AND check.")
        return None
    xs = [1.0 - Ls[r[0]] for r in usable]
    ys = [r[1][0] / r[1][harm] for r in usable]
    A0, B0, res = complex_affine_fit(xs, ys)
    print(f"\n  [bleed] Y = H1/H{harm + 1} vs (1-L):   Y = A + B*(1-L)")
    for r, x, y in zip(usable, xs, ys):
        print(f"    knob {r[0]:.2f}  (1-L) {x:.4f}   |Y| {abs(y):>9.2f}   "
              f"|fit| {abs(A0 + B0 * x):>9.2f}")
    print(f"    |A| {abs(A0):.3f}   |B| {abs(B0):.3f}   fit residual {res:.3f} "
          f"({res / (abs(A0) + 1e-30) * 100:.1f}% of |A|)")
    ratio = abs(B0) / (abs(A0) + 1e-30)
    print(f"    => CLEAN_1/OD_1 = {ratio:.4f}  ({db(ratio):+.2f} dB)  at the mixer inputs")
    return dict(L=Ls, clean_over_od=ratio, p=ps)


def main():
    print("=" * 78)
    print("MIXER LAW — BLEND/LEVEL, measured from existing captures")
    print("Topology verified at pixel zoom (session 8); see module docstring.")
    print("=" * 78)

    summary = {}
    for seg_name, f0 in TONES:
        print("\n" + "#" * 78)
        print(f"# TONE {f0:g} Hz")
        print("#" * 78)
        _rows, fits = blend_route(seg_name, f0)
        lv = level_route(seg_name, f0)
        summary[f0] = (fits, lv)

    print("\n" + "=" * 78)
    print("SUMMARY")
    print("=" * 78)
    print("  bleed@ref-od = clean-vs-OD AMPLITUDE ratio actually present in the output at")
    print("  BLEND max-OD / LEVEL noon / DRIVE noon. Negative = clean is quieter than OD.")
    print(f"\n  {'tone':>6} {'L(noon)':>9} {'taper p':>8} {'bleed (LEVEL rt)':>17} "
          f"{'bleed (BLEND rt)':>17}")
    for f0, (fits, s) in summary.items():
        if not s:
            continue
        Ln = s["L"].get(0.50, float("nan"))
        p = float(np.mean(s["p"])) if s["p"] else float("nan")
        b_lvl = (1.0 - Ln) * s["clean_over_od"]
        b_bl, _ = bleed_from_blend(fits[0][0], fits[0][1], Ln)
        print(f"  {f0:>6.0f} {Ln:>9.4f} {p:>8.3f} {db(b_lvl):>+16.2f}dB {db(b_bl):>+16.2f}dB")

    # How much does the headline depend on the one externally-supplied number, L_noon?
    print("\n  Sensitivity of the BLEND-route bleed to L(noon) — the only outside input:")
    print(f"  {'L(noon)':>9} " + " ".join(f"{f0:>10.0f}Hz" for f0 in summary))
    for Ltest in (0.15, 0.20, 0.23, 0.30, 0.3711):
        cells = []
        for f0, (fits, _s) in summary.items():
            b, _ = bleed_from_blend(fits[0][0], fits[0][1], Ltest)
            cells.append(f"{db(b):>+9.2f}dB")
        tag = "  <- shipped p=1.43" if abs(Ltest - 0.3711) < 1e-3 else ""
        print(f"  {Ltest:>9.4f} " + " ".join(cells) + tag)
    print(f"\n  For comparison, the SHIPPED model (kLevelTaperExp = {LEVEL_TAPER_EXP_NOMINAL}) has")
    Lnom = 0.5 ** LEVEL_TAPER_EXP_NOMINAL
    a_n, b_n = blend_max_coeffs(Lnom)
    print(f"  L(noon) = {Lnom:.4f}, mixing {a_n:.4f}*od + {b_n:.4f}*clean, i.e. a coefficient")
    print(f"  ratio of {db(b_n / a_n):+.2f} dB — the handover's '-4.0 dB'. NOTE that figure is the")
    print(f"  COEFFICIENT ratio only; the actual bleed also carries CLEAN_1/OD_1 (drive-dependent).")


if __name__ == "__main__":
    main()
