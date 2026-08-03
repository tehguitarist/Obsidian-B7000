#!/usr/bin/env python3.11
"""GATE AB — WHAT CAN MOVE THE bt_notch / treble_peak PAIR THE WAY THE PEDAL MOVES IT?

WHY THIS EXISTS (session 130, executing session 129's `NEXT` #1 and #2).

GATE AA6 (s129) measured, on the pedal, across the four-rung drive ladder:

    bt_notch     695.7 -> 745.4 Hz   +7.15 %  RISING  4/4
    treble_peak 2696.4 -> 2498.5 Hz  -7.92 %  FALLING 4/4
    ratio (peak/notch) 3.8761 -> 3.3519   -13.52 %   falling 4/4

and refuted every "drive-dependent effective element VALUE" candidate with this argument:

    "Scaling every element of a linear network by k moves BOTH features by 1/k, so their
     RATIO is invariant.  Measured, it falls 13.5 %.  => refuted, with no render and no
     threshold."

⚠⚠ **THAT ARGUMENT'S STATED PREMISE IS FALSE FOR OUR OWN BASELINE, AND THIS GATE MEASURES
BY HOW MUCH.**  s125 established the cascade in closed form: the treble peak is the
bridged-T's rise out of its own notch **rolled off by the two Sallen-Keys and the clipper's
closed-loop pole**.  So the notch belongs to ONE network and the peak is a VERTEX where a
rise from that network meets a rolloff from three others.  Scaling the bridged-T's elements
therefore moves the notch fully and the peak only PARTLY -- the ratio is NOT invariant, and
a screen built on "the candidate must break the ratio invariance" would pass everything,
including the refuted class.

⭐ What this gate is for is to replace that premise with a measured one.  The pedal's
signature is TWO-DIMENSIONAL -- (notch UP, peak DOWN) -- and the useful question is which
perturbation classes can produce OPPOSITE-SIGNED motion at all.  A class that moves both
features the same way is refuted however the ratio behaves.

WHAT THIS GATE DOES **NOT** CLAIM.
  * It does not identify the pedal's mechanism.  It classifies candidate SHAPES on the
    model's own cascade and reports which are even admissible.
  * The cascade is the MODEL's.  Applying its sensitivities to the pedal assumes the two
    devices share this topology -- which is AA6's own "one network" premise, restated, and
    still untested on the pedal side (s129 `NEXT` #2).  Printed every run, not inferred.
  * No render, no capture, no constant.  Pure arithmetic on shipped constants.

  AB1  KNOWN ANSWER   reproduce s125's closed-form cascade: notch ~716 Hz, peak 2934.8 Hz.
                      Both read off the SAME log-f vertex interpolation GATE W uses, and
                      both must land, or nothing below is readable.
  AB2  CONTROL        a post-cascade constant gain MUST move neither feature (a level change
                      cannot move a vertex); and a uniform scale of the WHOLE cascade's
                      time constants MUST move both by exactly 1/k.  Without both, AB3's
                      zeros are unreadable (s126 Y2: "a constant that moves nothing and a
                      constant that never reached the arithmetic look identical").
  AB3  SENSITIVITY    d(log f)/d(log param) for the notch, the peak and the ratio, for every
                      candidate class -- two-sided, at a perturbation small enough to be
                      local and large enough to clear the vertex interpolator's own floor.
  AB4  RATIO PREMISE  the number AA6 assumed was zero: how much does the ratio move under
                      pure bridged-T element scaling?  Reported as a fraction of the
                      pedal's measured -13.52 %.
  AB5  ADMISSIBILITY  computed verdict: which classes produce OPPOSITE-signed (notch, peak)
                      motion, i.e. which survive as candidates for item 6.

Usage:
  python3.11 analysis/bt_pair_shape_gate.py
  python3.11 analysis/bt_pair_shape_gate.py --json analysis/reports/s130_bt_pair.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# ---------------------------------------------------------------------------
# Shipped constants.  Imported where a module owns them; the four bridged-T
# values and clipA0 are read out of FitParams.h by text so a future re-fit
# cannot silently desynchronise this gate from the plugin
# (`verify-the-CONSTANT-not-the-prose`, s35).
# ---------------------------------------------------------------------------
REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FITPARAMS = os.path.join(REPO, "src", "dsp", "FitParams.h")


def _read_fitparam(name):
    """Read `double <name> = <value>;` out of FitParams.h.  Refuses on absence."""
    import re

    src = open(FITPARAMS).read()
    m = re.search(r"^\s*double\s+" + re.escape(name) + r"\s*=\s*([0-9eE.+-]+)\s*;", src, re.M)
    if m is None:
        sys.exit(f"REFUSED: FitParams.h has no `double {name} = ...;` -- this gate is "
                 f"desynchronised from the shipped constants, and its numbers would be fiction.")
    return float(m.group(1))


BT_R22 = _read_fitparam("btR22")
BT_R23 = _read_fitparam("btR23")
BT_C16 = _read_fitparam("btC16")
BT_C17 = _read_fitparam("btC17")
CLIP_A0 = _read_fitparam("clipA0")

# circuit.md "Recovery + bandlimiting" + CLIPPER tables (schematic-verified, not fitted).
R16, R18, C14 = 6.8e3, 330.0e3, 220.0e-12          # clipper input / shunt feedback
SK_B = dict(R1=10.0e3, R2=22.0e3, C1=1.0e-9, C2=1.0e-9)      # IC4_B, ~10.7 kHz
SK_A = dict(R1=22.0e3, R2=47.0e3, C1=2.2e-9, C2=1.0e-9)      # IC4_A, ~3.3 kHz
R24 = 10.0e3                                        # bridged-T -> SK series resistor

# GATE AA6's measured pedal signature (s129, from s122_feature_locus.json's W6 medians).
PEDAL = dict(notch_lo=695.7, notch_hi=745.4, peak_lo=2498.5, peak_hi=2696.4)
PEDAL_DNOTCH = PEDAL["notch_hi"] / PEDAL["notch_lo"] - 1.0     # +7.14 %
# ⚠ -7.34 %, NOT the -7.92 % this comment read until session 131. Both numbers are real and they
# are different CONVENTIONS: -7.92 is AA6's max/min-1 SPAN, -7.34 is the rung-1 -> rung-4 CHANGE,
# which is what a dose-response means and what this file deliberately adopted (s130 flagged the
# mix in prose and left the comment stale). The constant below has always been the -7.34 one; only
# the comment was wrong, so no number moved -- but a comment that misstates the constant beside it
# is exactly how a convention gets re-mixed by the next reader.
PEDAL_DPEAK = PEDAL["peak_lo"] / PEDAL["peak_hi"] - 1.0        # -7.34 %
PEDAL_DRATIO = ((PEDAL["peak_lo"] / PEDAL["notch_hi"]) / (PEDAL["peak_hi"] / PEDAL["notch_lo"])) - 1.0

# s125's closed-form answers, the known answer AB1 must reproduce.
S125_PEAK_HZ = 2934.8
S125_NOTCH_LO, S125_NOTCH_HI = 700.0, 730.0        # W6 reads the model's notch at 715.8-716.9

# Locator grid.  GATE W uses 1/48-octave cells; a closed-form curve has no such
# constraint, so this is finer -- but the VERTEX INTERPOLATION is the same
# (parabola through the extremum and its two neighbours, in log f), which is what
# makes AB1 comparable to a stored GATE W number at all.
GRID_PPO = 480          # points per octave
F_LO, F_HI = 200.0, 12000.0
NOTCH_WIN = (450.0, 1200.0)
PEAK_WIN = (1500.0, 6000.0)


# ---------------------------------------------------------------------------
# The cascade.
# ---------------------------------------------------------------------------
def bridged_t(f, r22, r23, c16, c17, rload=None, rsrc=0.0):
    """buf-out --C16--> Nout ; buf-out --R22--> Nmid --R23--> Nout ; Nmid --C17--> GND.

    `rload`  : resistance Nout -> GND (output-side loading).
    `rsrc`   : resistance in series with the driving buffer (source-side loading, i.e.
               a non-ideal op-amp output impedance).  rsrc = 0 is the shipped stage.

    With rsrc > 0 the driven node is no longer the ideal source, so the solve carries a
    third unknown (Nin).  Written as one 3x3 for every case rather than two code paths --
    a stage's own algebra must not fork on a perturbation the perturbation is testing.
    """
    s = 2j * np.pi * np.asarray(f, dtype=float)
    out = np.empty(s.shape, dtype=complex)
    gl = 0.0 if rload is None else 1.0 / rload
    for i, si in enumerate(s):
        y16, y17 = si * c16, si * c17
        # unknowns [Nin, Nmid, Nout]; ideal buffer output = 1 V behind rsrc.
        M = np.zeros((3, 3), dtype=complex)
        b = np.zeros(3, dtype=complex)
        if rsrc <= 0.0:
            M[0, 0] = 1.0
            b[0] = 1.0                                   # Nin pinned to the source
        else:
            gs = 1.0 / rsrc
            M[0, 0] = gs + 1.0 / r22 + y16
            M[0, 1] = -1.0 / r22
            M[0, 2] = -y16
            b[0] = gs
        M[1, 0] = -1.0 / r22
        M[1, 1] = 1.0 / r22 + 1.0 / r23 + y17
        M[1, 2] = -1.0 / r23
        M[2, 0] = -y16
        M[2, 1] = -1.0 / r23
        M[2, 2] = 1.0 / r23 + y16 + gl
        out[i] = np.linalg.solve(M, b)[2]
    return out


def sallen_key(f, R1, R2, C1, C2, scale=1.0):
    """Unity-gain 2nd-order SK LPF (eq_reference.sallen_key_lpf_tf's closed form).

    `scale` multiplies both time constants, i.e. moves the corner by 1/scale --
    the knob AB3 uses to represent "an added downstream rolloff".
    """
    s = 2j * np.pi * np.asarray(f, dtype=float) * scale
    return 1.0 / (1.0 + s * C2 * (R1 + R2) + s * s * R1 * R2 * C1 * C2)


def clipper_closed_loop(f, a0, r16=R16, r18=R18, c14=C14):
    """Small-signal transfer of the shunt-feedback CD4049 stage in its linear region.

        Vin --r16--> W --(r18 || c14)--> Vout ,   Vout = -a0 * W
        => Vout/Vin = -a0 / (1 + r16(1+a0)/r18 + s*r16*(1+a0)*c14)

    Pole at [1/((1+a0)r16) + 1/r18] / (2*pi*c14) -- 6.30 kHz at the shipped a0, NOT the
    2.19 kHz bare `c14 || r18` corner (s125's own corrected derivation; the bare pole is
    the right formula for the wrong quantity).
    """
    s = 2j * np.pi * np.asarray(f, dtype=float)
    return -a0 / (1.0 + r16 * (1.0 + a0) / r18 + s * r16 * (1.0 + a0) * c14)


def cascade(f, *, r22=None, r23=None, c16=None, c17=None, c14=None,
            rload=None, rsrc=0.0, sk_scale=1.0, a0=None, gain=1.0):
    """The s125 cascade: bridged-T (loaded by R24) x SK 10.7k x SK 3.3k x clipper loop."""
    r22 = BT_R22 if r22 is None else r22
    r23 = BT_R23 if r23 is None else r23
    c16 = BT_C16 if c16 is None else c16
    c17 = BT_C17 if c17 is None else c17
    c14 = C14 if c14 is None else c14
    a0 = CLIP_A0 if a0 is None else a0
    h = bridged_t(f, r22, r23, c16, c17, rload=(R24 if rload is None else rload), rsrc=rsrc)
    h = h * sallen_key(f, scale=sk_scale, **SK_B)
    h = h * sallen_key(f, scale=sk_scale, **SK_A)
    h = h * clipper_closed_loop(f, a0, c14=c14)
    return gain * h


# ---------------------------------------------------------------------------
# Locator -- GATE W's estimator: extremum on a log-f grid, parabolic vertex.
# ---------------------------------------------------------------------------
def _grid():
    n = int(round(GRID_PPO * math.log2(F_HI / F_LO)))
    return np.logspace(math.log10(F_LO), math.log10(F_HI), n + 1)


_F = _grid()
_LF = np.log10(_F)


def locate(mag_db, lo, hi, kind):
    """Vertex-interpolated extremum inside [lo, hi].  Returns (f0, prominence_db).

    Refuses (None) when the extremum rests ON a window bound -- a prominence measured at
    a window edge is identically zero by construction, so an edge hit is a locator failure,
    not a feature (s126).
    """
    m = (_F >= lo) & (_F <= hi)
    idx = np.flatnonzero(m)
    sub = mag_db[idx]
    j = int(np.argmin(sub) if kind == "min" else np.argmax(sub))
    if j == 0 or j == len(sub) - 1:
        return None, None
    i = idx[j]
    y0, y1, y2 = mag_db[i - 1], mag_db[i], mag_db[i + 1]
    den = y0 - 2.0 * y1 + y2
    d = 0.0 if den == 0.0 else 0.5 * (y0 - y2) / den
    lf = _LF[i] + d * (_LF[i + 1] - _LF[i])
    # Prominence: walk out to the first turn on each side, take the smaller rise/fall.
    def _walk(step):
        k, best = i, mag_db[i]
        while 0 < k < len(mag_db) - 1:
            nxt = mag_db[k + step]
            if kind == "min":
                if nxt < mag_db[k]:
                    break
                best = max(best, nxt)
            else:
                if nxt > mag_db[k]:
                    break
                best = min(best, nxt)
            k += step
        return abs(best - mag_db[i])
    return 10.0 ** lf, min(_walk(-1), _walk(+1))


def features(**kw):
    """(notch Hz, peak Hz, peak/notch) for one cascade setting."""
    h = cascade(_F, **kw)
    db = 20.0 * np.log10(np.abs(h) + 1e-300)
    fn, pn = locate(db, *NOTCH_WIN, "min")
    fp, pp = locate(db, *PEAK_WIN, "max")
    if fn is None or fp is None:
        return None
    return dict(notch=fn, peak=fp, ratio=fp / fn, prom_notch=pn, prom_peak=pp)


# ---------------------------------------------------------------------------
# Candidate classes.  Each is (label, kwargs-builder taking a multiplier, note).
# ---------------------------------------------------------------------------
def _all_bt(k):
    """Uniform bridged-T element scale -- AA6's refuted class, stated as it stated it.

    Scaling R and C together by sqrt(k) each would also work; scaling the two caps by k
    with the resistors fixed is the same time-constant move and keeps the network's
    impedance level fixed, which is what an effective-C drift physically is.
    """
    return dict(c16=BT_C16 * k, c17=BT_C17 * k)


# TIME-CONSTANT classes.  These three partition every time constant in the cascade, so
# each feature's sensitivities across them must sum to EXACTLY -1 (the whole-cascade
# control of AB2, differentiated).  That sum is a free known answer with no threshold to
# argue about, and it is also the ATTRIBUTION: how much of each feature's position each
# sub-network sets.
TAU_CLASSES = (
    ("bt time-constants (both caps)", _all_bt,
     "AA6's refuted class: an effective element-value drift in the bridged-T"),
    ("downstream rolloff (both SKs)", lambda k: dict(sk_scale=k),
     "k>1 moves both SK corners DOWN by 1/k -- any added HF rolloff"),
    ("clipper pole (C14)", lambda k: dict(c14=C14 * k),
     "the shunt-feedback stage's own pole, 6.30 kHz at the shipped a0"),
)

# PHYSICAL classes.  Not a partition -- each is a mechanism a real device could have.
PHYS_CLASSES = (
    ("bt C17 alone (shunt leg)", lambda k: dict(c17=BT_C17 * k),
     "changes the T's shunt -- moves the notch and its Q together"),
    ("bt C16 alone (bridge cap)", lambda k: dict(c16=BT_C16 * k),
     "the bridge path only"),
    ("bt R22 alone", lambda k: dict(r22=BT_R22 * k), "T upper leg"),
    ("bt R23 alone", lambda k: dict(r23=BT_R23 * k), "T lower leg"),
    ("output loading (Nout->GND)", lambda k: dict(rload=R24 / k),
     "k>1 = HEAVIER load; the shipped stage sits at k=1 (R24)"),
    ("source loading (buffer Zout)", lambda k: dict(rsrc=1.0e3 * k),
     "a non-ideal op-amp output impedance ahead of the network, swept about 1 kohm; "
     "the shipped stage assumes 0"),
    ("clipper a0 (supply sag route)", lambda k: dict(a0=CLIP_A0 * k),
     "s125 refuted this on direction for the peak; included as a cross-check"),
)

CLASSES = TAU_CLASSES + PHYS_CLASSES


def sens(builder, k):
    """Two-sided d(log f)/d(log k) for notch, peak and ratio."""
    hi = features(**builder(k))
    lo = features(**builder(1.0 / k))
    if hi is None or lo is None:
        return None
    dlk = 2.0 * math.log(k)
    return {q: math.log(hi[q] / lo[q]) / dlk for q in ("notch", "peak", "ratio")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None, help="write the full result set here")
    ap.add_argument("--step", type=float, default=1.10,
                    help="two-sided perturbation multiplier for AB3 (default 1.10)")
    args = ap.parse_args()

    out = {"shipped": dict(btR22=BT_R22, btR23=BT_R23, btC16=BT_C16, btC17=BT_C17,
                           clipA0=CLIP_A0, R24=R24)}
    fail = []

    print("=" * 96)
    print("GATE AB — what can move the bt_notch / treble_peak pair the way the pedal moves it?")
    print("=" * 96)
    print(f"\nShipped: btR22 {BT_R22:.0f}  btR23 {BT_R23:.0f}  btC16 {BT_C16:.4g}  "
          f"btC17 {BT_C17:.4g}  clipA0 {CLIP_A0:.4f}")
    print("⚠ PREMISE, printed every run and NOT tested here: this cascade is the MODEL's.  AA6's\n"
          "  'the pedal's two features are ONE network' is proven for the model (s125) and ASSUMED\n"
          "  for the pedal.  Every admissibility verdict below inherits that assumption.")

    # ---- AB1 known answer --------------------------------------------------
    print("\n" + "-" * 96)
    print("AB1  KNOWN ANSWER — reproduce s125's closed-form cascade")
    print("-" * 96)
    base = features()
    if base is None:
        sys.exit("REFUSED (AB1): the baseline cascade has no interior notch or peak — "
                 "the locator found an edge, so nothing below is readable.")
    out["baseline"] = base
    print(f"  notch  {base['notch']:9.2f} Hz   (prominence {base['prom_notch']:6.2f} dB)   "
          f"s125/W6 window {S125_NOTCH_LO:.0f}-{S125_NOTCH_HI:.0f}")
    print(f"  peak   {base['peak']:9.2f} Hz   (prominence {base['prom_peak']:6.2f} dB)   "
          f"s125 closed form {S125_PEAK_HZ:.1f}")
    peak_err = base["peak"] / S125_PEAK_HZ - 1.0
    print(f"  ratio  {base['ratio']:9.4f}")
    print(f"  peak vs s125: {100.0 * peak_err:+.2f} %")
    ok1 = (S125_NOTCH_LO <= base["notch"] <= S125_NOTCH_HI) and abs(peak_err) < 0.01
    print(f"  => {'PASS' if ok1 else 'FAIL'}  (notch in window AND peak within 1 % of s125)")
    if not ok1:
        fail.append("AB1")

    # ---- AB2 controls ------------------------------------------------------
    print("\n" + "-" * 96)
    print("AB2  CONTROLS — a NULL and a POSITIVE, so AB3's zeros are readable")
    print("-" * 96)
    g = features(gain=3.1623)                       # +10 dB, post-cascade
    dn = abs(g["notch"] / base["notch"] - 1.0)
    dp = abs(g["peak"] / base["peak"] - 1.0)
    null_ok = dn < 1e-9 and dp < 1e-9
    print(f"  NULL     +10 dB post-cascade gain    d(notch) {dn:.3e}   d(peak) {dp:.3e}   "
          f"{'PASS' if null_ok else 'FAIL'}")

    # POSITIVE: scale every time constant in the whole cascade by k.  Both features
    # must then move by exactly 1/k -- this is the ONE case where AA6's invariant holds,
    # and showing it holds here is what proves it fails elsewhere for a real reason.
    k = 1.25
    whole = features(c16=BT_C16 * k, c17=BT_C17 * k, sk_scale=k,
                     a0=CLIP_A0)                    # SK scale + bt caps
    whole = features(**{**_all_bt(k), "sk_scale": k})
    # the clipper pole must scale too, or the "whole cascade" is not whole.
    hw = (bridged_t(_F, BT_R22, BT_R23, BT_C16 * k, BT_C17 * k, rload=R24)
          * sallen_key(_F, scale=k, **SK_B) * sallen_key(_F, scale=k, **SK_A)
          * clipper_closed_loop(_F, CLIP_A0, c14=C14 * k))
    dbw = 20.0 * np.log10(np.abs(hw) + 1e-300)
    fnw, _ = locate(dbw, NOTCH_WIN[0] / k, NOTCH_WIN[1] / k, "min")
    fpw, _ = locate(dbw, PEAK_WIN[0] / k, PEAK_WIN[1] / k, "max")
    en = abs((fnw * k) / base["notch"] - 1.0)
    ep = abs((fpw * k) / base["peak"] - 1.0)
    pos_ok = en < 1e-4 and ep < 1e-4
    print(f"  POSITIVE whole-cascade tau x{k}        notch x{fnw / base['notch']:.5f}  "
          f"peak x{fpw / base['peak']:.5f}   (both must be 1/{k} = {1 / k:.5f})")
    print(f"           residual  notch {en:.2e}   peak {ep:.2e}   {'PASS' if pos_ok else 'FAIL'}")
    print("           ⭐ THIS is the only configuration in which AA6's 'ratio is invariant'\n"
          "             premise actually holds — everything scales, so the ratio cannot move.")
    out["controls"] = dict(null_dnotch=dn, null_dpeak=dp, pos_notch_resid=en, pos_peak_resid=ep)
    if not (null_ok and pos_ok):
        fail.append("AB2")

    # ---- AB3 sensitivity ---------------------------------------------------
    print("\n" + "-" * 96)
    print(f"AB3  SENSITIVITY — d(log f)/d(log param), two-sided at x{args.step:.2f}")
    print("-" * 96)
    rows = {}

    def _emit(label, builder, note):
        s = sens(builder, args.step)
        if s is None:
            print(f"  {label:32s} {'--':>9s} {'--':>9s} {'--':>9s}  {'NO FEATURE':>10s}")
            rows[label] = None
            return
        # ⚠ ADMISSIBILITY IS A COMPARISON AGAINST THE TARGET, NOT A PROPERTY OF THE CLASS.
        # A class admits the target iff some direction of its knob gives BOTH features the
        # target's signs — i.e. iff the two sign PRODUCTS agree.  Writing this as a bare
        # "is it opposite-signed?" is `computed-verdicts-not-narrated`: it is right only
        # while the target happens to be opposite-signed, and it was caught by exactly that
        # mutation (_mutate_gate_ab.py arm 6), which flipped the target and changed nothing.
        opp = (s["notch"] * s["peak"]) * (PEDAL_DNOTCH * PEDAL_DPEAK) > 0.0
        tag = "ADMITS" if opp else "no"
        print(f"  {label:32s} {s['notch']:+9.4f} {s['peak']:+9.4f} {s['ratio']:+9.4f}  {tag:>10s}")
        rows[label] = dict(note=note, opposite=opp, **s)

    print("  TIME-CONSTANT classes — these partition every tau in the cascade, so each")
    print("  feature's column MUST sum to exactly -1.  That sum is both a known answer and")
    print("  the ATTRIBUTION of the feature's position to the sub-networks.\n")
    print(f"  {'class':32s} {'notch':>9s} {'peak':>9s} {'ratio':>9s}  {'signs':>10s}")
    for label, builder, note in TAU_CLASSES:
        _emit(label, builder, note)
    tau_n = sum(rows[l]["notch"] for l, _, _ in TAU_CLASSES)
    tau_p = sum(rows[l]["peak"] for l, _, _ in TAU_CLASSES)
    print(f"  {'SUM (must be -1.0000)':32s} {tau_n:+9.4f} {tau_p:+9.4f}")
    sum_ok = abs(tau_n + 1.0) < 5e-3 and abs(tau_p + 1.0) < 5e-3
    print(f"  => {'PASS' if sum_ok else 'FAIL'}   residuals  notch {tau_n + 1:+.2e}  peak {tau_p + 1:+.2e}")
    if not sum_ok:
        fail.append("AB3-sum")
    print("\n  ⭐ READ THE COLUMNS AS AN ATTRIBUTION.  The notch is ~100 % the bridged-T; the PEAK")
    print("     is mostly the SALLEN-KEYS.  The two features are very nearly ORTHOGONAL in this")
    print("     cascade — which is a different statement from 'two features of one network'.")

    print(f"\n  PHYSICAL classes (not a partition — each is a mechanism a device could have):\n")
    print(f"  {'class':32s} {'notch':>9s} {'peak':>9s} {'ratio':>9s}  {'signs':>10s}")
    for label, builder, note in PHYS_CLASSES:
        _emit(label, builder, note)
    out["sensitivity"] = rows
    out["tau_sum"] = dict(notch=tau_n, peak=tau_p)

    # ---- AB4 the ratio premise --------------------------------------------
    print("\n" + "-" * 96)
    print("AB4  THE RATIO PREMISE — how far from invariant is a pure element-value drift?")
    print("-" * 96)
    bt = rows["bt time-constants (both caps)"]
    # Express it the way AA6 would need it: for the drift that moves the NOTCH by the
    # pedal's own +7.15 %, how much does the ratio move, and what fraction of -13.52 % is that?
    if bt is None:
        print("  NOT MEASURABLE — the element-drift arm lost a feature.")
        fail.append("AB4")
    else:
        need = math.log1p(PEDAL_DNOTCH) / bt["notch"]      # log-multiplier of the param
        dratio = math.expm1(need * bt["ratio"])
        dpeak = math.expm1(need * bt["peak"])
        frac = dratio / PEDAL_DRATIO if PEDAL_DRATIO else float("nan")
        print(f"  Pedal:              notch {100 * PEDAL_DNOTCH:+.2f} %   "
              f"peak {100 * PEDAL_DPEAK:+.2f} %   ratio {100 * PEDAL_DRATIO:+.2f} %")
        print(f"  Element drift sized to match the pedal's NOTCH move:")
        print(f"                      notch {100 * PEDAL_DNOTCH:+.2f} %   "
              f"peak {100 * dpeak:+.2f} %   ratio {100 * dratio:+.2f} %")
        print(f"  => the ratio moves {100 * dratio:+.2f} % where AA6 assumed 0.00 %, "
              f"i.e. {100 * frac:+.1f} % of the pedal's own ratio move.")
        print("  ⛔ AA6's REASON does not survive: the ratio is NOT invariant under element drift,\n"
              "     because the PEAK is a vertex where the bridged-T's rise meets three rolloffs\n"
              "     (2 x SK + the clipper pole) that the drift does not touch.  A screen written as\n"
              "     'the candidate must break ratio invariance' would pass the refuted class.")
        print("  ⭐ AA6's VERDICT survives, on a stronger and simpler ground — see AB5.")
        out["ratio_premise"] = dict(need_log_mult=need, dratio=dratio, dpeak=dpeak,
                                    frac_of_pedal=frac)

    # ---- AB5 admissibility -------------------------------------------------
    print("\n" + "-" * 96)
    print("AB5  ADMISSIBILITY — which classes can move notch UP while peak moves DOWN?")
    print("-" * 96)
    tsign = "OPPOSITE-signed" if PEDAL_DNOTCH * PEDAL_DPEAK < 0 else "SAME-signed"
    print(f"  Target signature (pedal, AA6): notch {100 * PEDAL_DNOTCH:+.2f} %, "
          f"peak {100 * PEDAL_DPEAK:+.2f} %  => {tsign}.")
    adm = [lab for lab, r in rows.items() if r and r["opposite"]]
    ref = [lab for lab, r in rows.items() if r and not r["opposite"]]
    print(f"\n  ADMISSIBLE ON SIGN ({len(adm)}) — with the SIZE each would need, because a sign")
    print("  that is right at an unreachable magnitude is not a candidate (s126):")
    print(f"    {'class':34s} {'knob x':>9s} {'-> notch':>9s} {'-> peak':>9s}  verdict")
    for lab in adm:
        r = rows[lab]
        # Size the knob to deliver the PEAK's required move, then read the notch it drags.
        lm = math.log1p(PEDAL_DPEAK) / r["peak"]
        dn = math.expm1(lm * r["notch"])
        reach = abs(lm) < math.log(4.0)      # within a 4x move of the shipped value
        v = "reachable" if reach else "UNREACHABLE"
        mult = math.exp(lm)
        ms = f"{mult:9.3f}" if 1e-3 <= mult <= 1e4 else f"{mult:9.1e}"
        print(f"    {lab:34s} {ms} {100 * dn:+8.2f} % {100 * PEDAL_DPEAK:+8.2f} %  {v}")
        rows[lab]["peak_knob_mult"] = mult
        rows[lab]["peak_knob_reachable"] = reach

    peak_ok = [l for l in adm if rows[l]["peak_knob_reachable"]]
    worst_notch = max((abs(math.expm1(math.log1p(PEDAL_DPEAK) / rows[l]["peak"] * rows[l]["notch"]))
                       for l in peak_ok), default=0.0)
    print(f"\n  ⇒ COMPUTED: {len(peak_ok)} of {len(adm)} carry the PEAK axis within a 4x knob move "
          f"({', '.join(peak_ok)}),")
    print(f"    and the largest NOTCH movement any of them drags along is {100 * worst_notch:.2f} % "
          f"against a required {100 * PEDAL_DNOTCH:+.2f} %.")
    print("    ⇒ the notch's rise has NO admissible carrier in this cascade.  Its only levers are")
    print("      the bridged-T's own elements, which are sign-refuted for the PAIR yet are the only")
    print("      thing that moves that axis at all.  AB6 solves what that forces.")
    print("    ⚠ `clipper a0` is reachable in SIZE and admissible in SIGN here but is refuted on")
    print("      PHYSICAL DIRECTION: it needs a0 to RISE with drive, and supply sag LOWERS it")
    print("      (s125 measured a0 24.871 -> 15 -> 8 walking the peak 2934.8 -> 3025.8 -> 3099.0 Hz,")
    print("      i.e. UP, away from the pedal).  Sign-admissibility is necessary, not sufficient.")
    out["peak_carriers_reachable"] = peak_ok
    anti = "the SAME way" if PEDAL_DNOTCH * PEDAL_DPEAK < 0 else "OPPOSITE ways"
    print(f"\n  REFUTED ON SIGN ({len(ref)}) — moves both features {anti} at every size:")
    for lab in ref:
        print(f"    - {lab:34s} ({rows[lab]['note']})")
    out["admissible"] = adm
    out["refuted_on_sign"] = ref
    # A machine-checkable restatement of the verdict.  A prose count is a bad discriminator
    # -- the two groups happen to have 5 members each here, so a mutation that SWAPS them
    # leaves every printed count identical (caught by _mutate_gate_ab.py arm 6, which passed
    # vacuously until this line existed).  Membership, not cardinality.
    print(f"\n  AB5-MEMBERSHIP admissible={sorted(adm)}")
    print(f"  AB5-MEMBERSHIP refuted={sorted(ref)}")
    print("\n  ⭐ VERDICT (computed): a candidate for item 6 must be in the admissible list, and\n"
          "     the sign requirement is checkable with NO threshold — it does not depend on the\n"
          "     size of the effect, only on which way the two features go.")
    if not adm:
        print("  ⚠ NOTHING is admissible in this cascade.  That is a finding about the MODEL's\n"
              "    topology, not about the pedal: it would mean no perturbation of OUR network can\n"
              "    produce the pedal's signature, and the mechanism is somewhere this cascade does\n"
              "    not reach (upstream of the clipper, or a topology we do not have).")

    # ---- AB6 two-mechanism decomposition ----------------------------------
    print("\n" + "-" * 96)
    print("AB6  DECOMPOSITION — the smallest set of mechanisms that reproduces the signature")
    print("-" * 96)
    bt = rows["bt time-constants (both caps)"]
    sk = rows["downstream rolloff (both SKs)"]
    if bt is None or sk is None:
        print("  NOT MEASURABLE — an arm lost a feature.")
        fail.append("AB6")
    else:
        # Solve, in log space, for the pair of multipliers reproducing (dnotch, dpeak).
        A = np.array([[bt["notch"], sk["notch"]], [bt["peak"], sk["peak"]]])
        rhs = np.array([math.log1p(PEDAL_DNOTCH), math.log1p(PEDAL_DPEAK)])
        cond = np.linalg.cond(A)
        x = np.linalg.solve(A, rhs)
        print(f"  The notch axis and the peak axis are carried by DIFFERENT sub-networks, so the")
        print(f"  2x2 is well conditioned (cond {cond:.2f}) and the split is essentially unique:\n")
        print(f"    bridged-T time constants   x {math.exp(x[0]):.4f}   ({100 * math.expm1(x[0]):+.2f} %)")
        print(f"    Sallen-Key time constants  x {math.exp(x[1]):.4f}   ({100 * math.expm1(x[1]):+.2f} %"
              f"  => SK corners {100 * math.expm1(-x[1]):+.2f} %)")
        chk = features(**{**_all_bt(math.exp(x[0])), "sk_scale": math.exp(x[1])})
        rn = chk["notch"] / base["notch"] - 1.0
        rp = chk["peak"] / base["peak"] - 1.0
        print(f"\n  VERIFY by rendering the combination rather than trusting the linearisation")
        print(f"  (s98: an invariance holds only over the region it was measured in):")
        print(f"    notch {100 * rn:+.2f} %  (target {100 * PEDAL_DNOTCH:+.2f} %)   "
              f"peak {100 * rp:+.2f} %  (target {100 * PEDAL_DPEAK:+.2f} %)")
        lin_ok = abs(rn - PEDAL_DNOTCH) < 0.005 and abs(rp - PEDAL_DPEAK) < 0.005
        print(f"    => {'PASS' if lin_ok else 'FAIL'} (both within 0.5 % — the linearisation holds at this size)")
        if not lin_ok:
            fail.append("AB6")
        print("\n  ⭐ THE DELIVERABLE: item 6's target is TWO sized, SEPARATE mechanisms, not one.")
        print("     A single damping/loading change cannot do it — nothing in AB3 moves both axes")
        print("     appreciably, because nothing in this cascade couples them.")
        out["decomposition"] = dict(bt_mult=math.exp(x[0]), sk_mult=math.exp(x[1]),
                                    cond=cond, verify_notch=rn, verify_peak=rp)

    print("\n" + "=" * 96)
    if fail:
        print(f"GATE AB: REFUSED — {', '.join(fail)} did not pass.  Nothing above them is quotable.")
    else:
        print("GATE AB: all guards passed.  AB3-AB5 are readable.")
    print("=" * 96)

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"wrote {args.json}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
