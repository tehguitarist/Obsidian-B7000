#!/usr/bin/env python3.11
"""GATE AF — CAN ANY PHYSICAL MECHANISM MAKE THE POST-CLIPPER SK BANDWIDTH DRIVE-DEPENDENT?

WHY THIS EXISTS (session 134, executing sessions 132/133's `NEXT` #1).

GATE AB6 (s130) sized open work item 6's treble-peak half as a **Sallen-Key** move:

    SK time constants x 1.1113  (SK corners -10.01 %)  =>  peak -7.98 % vs a -7.34 % target

and named its physical carrier in one line, which nothing has ever computed:

    "A falling effective op-amp GBW under large signal is the obvious single physical
     cause of the SK half."                                   -- s130 session log

GATE AC (s132) then reconciled that axis against GATE I and cleared it to be BUILT.  So the
next step was to write the DSP.  ⛔ **This gate exists because the step before writing DSP is
to ask what would physically produce the required move, and whether anything reaches** --
`localise-before-fitting-a-constant`, and s125's sharper form of it (localise your own side's
mechanism in closed form BEFORE theorising; it takes minutes and it can retire a whole family
of candidates before a single render).

⭐ It is the same shape as s125's own self-caught error: that session wrote a mechanism
(dynamic supply sag walking the `C14 || R18` corner) into CLAUDE.md, computed it in the same
hour, and found the corner was 6.29 kHz rather than 2.19 and moved the WRONG WAY.  The
falsifier was written next to the hypothesis.  This gate is that falsifier for the SK half.

WHAT IT DOES **NOT** CLAIM.
  * It does not identify the pedal's mechanism.  It screens candidates for OUR cascade and
    reports which are even reachable.
  * The cascade is the MODEL's -- s125's closed form, imported from GATE AB rather than
    re-derived.  Applying it to the pedal inherits AA6's "one network" premise, still
    untested on the pedal side (s129 `NEXT` #2).  Printed every run.
  * The two device parameters (TL072 GBW, slew rate) are DATASHEET typicals, not measured
    in this repo and not fitted.  Both refutations below are quoted at the WORSE end of the
    published spread so the verdict does not rest on the typical value.
  * No render, no capture, no constant, no `src/` edit.  Closed-form arithmetic plus two
    stored reports.

  AF1  KNOWN ANSWERS  (a) the finite-GBW Sallen-Key must reduce to the shipped IDEAL closed
                      form as ft -> inf -- without this, every number in AF2 is a property of
                      a typo; (b) the cascade must reproduce GATE AB1's peak (inherited);
                      (c) the vertex law `dx = -T/C` must predict AF6's measured tilt from
                      the curvature alone.  (c) is free and it is the one that certifies the
                      REFRAME rather than the refutations.
  AF2  GBW           what gain-bandwidth is required to move the peak onto target, against
                     what a TL072 has.  Plus the by-product: what the model's ideal-op-amp
                     assumption is costing at this feature today.
  AF3  SLEW          worst-case |dV/dt| the chain can present at either SK output, against
                     the TL072's slew rate.  Full-rail square wave = the harshest thing the
                     clipper can hand them, so this is an upper bound, not a sample.
  AF4  RAIL CLAMP    the model ALREADY carries a post-clipper amplitude nonlinearity on both
                     SK outputs, shipped and enabled.  GATE W6 has already measured what it
                     does to the peak.  Read from the stored report, not re-derived.
  AF5  PARASITICS    ceilings for the small candidates (op-amp input capacitance, film-cap
                     voltage coefficient) -- stated as ceilings because that is all they can
                     be, and a ceiling is enough to refute when the requirement is 10 %.
  AF6  THE REFRAME   the peak is a VERTEX (AB4).  A vertex moves under a drive-dependent
                     SLOPE change with NO corner moving anywhere.  Size that slope, and
                     check it against the drive-dependent term the project has already
                     measured (GATE Q's D(f)).
  AF7  VERDICT       computed, per candidate, against the target -- never a property of the
                     candidate alone (AB5's own defect, fixed there and not repeated here).

Usage:
  python3.11 analysis/sk_mechanism_locus.py
  python3.11 analysis/sk_mechanism_locus.py --json analysis/reports/s134_sk_mechanism.json
"""
import argparse
import json
import math
import os
import re
import sys

import numpy as np
from scipy.optimize import brentq

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import bt_pair_shape_gate as AB  # noqa: E402  -- the cascade, imported not transcribed

REPO = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FITPARAMS = os.path.join(REPO, "src", "dsp", "FitParams.h")
W_REPORT = os.path.join(REPO, "analysis", "reports", "s122_feature_locus.json")

# ---------------------------------------------------------------------------
# Device parameters.  ⚠ DATASHEET VALUES, NOT MEASURED HERE AND NOT FITTED.
#
# TI TL07x (circuit.md: IC4_A/IC4_B are TL072ACP).  Both refutations below are
# quoted at the end of the published spread that is WORST for this gate's
# conclusion -- the MINIMUM gain-bandwidth and the MINIMUM slew rate -- so that
# "the part is at the bad end of its spread" is not an escape route.
# ---------------------------------------------------------------------------
TL07X_GBW_TYP = 3.0e6      # Hz
TL07X_GBW_MIN = 2.5e6      # Hz   <- the number AF2's verdict is quoted against
TL07X_SR_TYP = 13.0        # V/us
TL07X_SR_MIN = 8.0         # V/us <- the number AF3's verdict is quoted against

# Parasitic ceilings (handbook, order-of-magnitude -- used ONLY as ceilings).
TL07X_CIN_PF = 3.0         # JFET-input common-mode input capacitance, ~3 pF
FILM_VCOEF_PER_V = 1.0e-3  # generous ceiling on |dC/C| per volt for a film cap


def _die(msg):
    """Refuse.  Exit 2, so a runner can tell a fired guard from an uncaught crash (s133).

    Defined above the constant reads deliberately: a desynchronised FitParams.h is a REFUSAL
    like any other and must not exit 1, which is also what `sys.exit("...")` and the
    guard-failure path below use.
    """
    print("\n" + "=" * 96)
    print(f"GATE AF: REFUSED — {msg}")
    print("=" * 96)
    sys.exit(2)


def _read_fitparam(name, kind="double"):
    src = open(FITPARAMS).read()
    m = re.search(r"^\s*" + kind + r"\s+" + re.escape(name) + r"\s*=\s*([A-Za-z0-9eE.+-]+)\s*;",
                  src, re.M)
    if m is None:
        _die(f"FitParams.h has no `{kind} {name} = ...;` — this gate is desynchronised from "
             f"the shipped constants, and its numbers would be fiction.")
    return m.group(1)


RAIL_NEG = abs(float(_read_fitparam("railNeg")))
RAIL_POS = abs(float(_read_fitparam("railPos")))
RAIL_ENABLED = _read_fitparam("railEnabled", kind="bool").strip() == "true"
RAIL_MAX = max(RAIL_NEG, RAIL_POS)

F = AB._F
L2 = np.log2(F)


def peak_of(db):
    return AB.locate(db, *AB.PEAK_WIN, "max")


def notch_of(db):
    return AB.locate(db, *AB.NOTCH_WIN, "min")


def db_of(h):
    return 20.0 * np.log10(np.abs(h) + 1e-300)


# ---------------------------------------------------------------------------
# The finite-GBW Sallen-Key.
#
# The shipped stage models the op-amp as IDEAL.  Give the voltage follower a
# one-pole open-loop gain A(s) = wt/s, so its closed-loop response is
# K(s) = A/(1+A) = 1/(1 + s/wt), and re-solve the same two nodes SallenKeyLPF.h
# solves (its own header's node graph, unchanged):
#
#   Vin --R1--> X --R2--> Y ;  Y --C2--> GND ;  C1 from X to Vout ;  Vout = K*Y
#
#   node Y :  (Y-X)/R2 + s*C2*Y = 0                  =>  X = Y*(1 + s*R2*C2)
#   node X :  (X-Vin)/R1 + (X-Y)/R2 + s*C1*(X-Vout) = 0
#
#   => H = K / [ 1 + s*R2*C2 + s*C2*R1 + s*R1*C1*(1 + s*R2*C2 - K) ]
#
# At K = 1 the bracket collapses to 1 + s*C2*(R1+R2) + s^2*R1*R2*C1*C2, i.e. the
# shipped closed form exactly -- which is what AF1a asserts numerically rather
# than by reading the algebra.
# ---------------------------------------------------------------------------
def sk_finite_gbw(f, R1, R2, C1, C2, ft, c2_extra=0.0):
    s = 2j * np.pi * np.asarray(f, dtype=float)
    c2 = C2 + c2_extra
    K = 1.0 / (1.0 + s / (2.0 * np.pi * ft))
    den = 1.0 + s * R2 * c2 + s * c2 * R1 + s * R1 * C1 * (1.0 + s * R2 * c2 - K)
    return K / den


def cascade_gbw(f, ft, c2_extra=0.0):
    """The s125 cascade with both Sallen-Keys given a finite-GBW op-amp."""
    h = AB.bridged_t(f, AB.BT_R22, AB.BT_R23, AB.BT_C16, AB.BT_C17, rload=AB.R24)
    h = h * sk_finite_gbw(f, ft=ft, c2_extra=c2_extra, **AB.SK_B)
    h = h * sk_finite_gbw(f, ft=ft, c2_extra=c2_extra, **AB.SK_A)
    return h * AB.clipper_closed_loop(f, AB.CLIP_A0)


def sk_ideal(f, R1, R2, C1, C2):
    s = 2j * np.pi * np.asarray(f, dtype=float)
    return 1.0 / (1.0 + s * C2 * (R1 + R2) + s * s * R1 * R2 * C1 * C2)


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    args = ap.parse_args()

    out, fail = {}, []
    TGT_PEAK = AB.PEDAL_DPEAK
    TGT_NOTCH = AB.PEDAL_DNOTCH

    print("=" * 96)
    print("GATE AF — can any PHYSICAL mechanism make the post-clipper SK bandwidth drive-dependent?")
    print("=" * 96)
    print(f"  cascade + locator imported from bt_pair_shape_gate (GATE AB); "
          f"rails read from FitParams.h")
    print(f"  target (GATE AA6, pedal, across the drive ladder): "
          f"peak {100*TGT_PEAK:+.2f} %   notch {100*TGT_NOTCH:+.2f} %")
    print("  ⚠ PREMISE, printed every run: this is the MODEL's cascade.  Carrying its")
    print("    sensitivities to the pedal assumes the two devices share this topology —")
    print("    AA6's 'one network' premise, still untested on the pedal side (s129 NEXT #2).")

    # ================= AF1  KNOWN ANSWERS ==================================
    print("\n" + "-" * 96)
    print("AF1  KNOWN ANSWERS")
    print("-" * 96)

    h_ideal = AB.cascade(F)
    db_ideal = db_of(h_ideal)
    p0, prom0 = peak_of(db_ideal)
    n0, _ = notch_of(db_ideal)
    if p0 is None or n0 is None:
        _die("AF1b — the baseline cascade lost a feature; nothing below is readable.")

    # (a) finite-GBW SK must reduce to the shipped ideal form as ft -> inf.
    p_inf, _ = peak_of(db_of(cascade_gbw(F, 1.0e12)))
    if p_inf is None:
        _die("AF1a — the finite-GBW cascade lost the peak at ft -> inf.")
    resid = abs(p_inf - p0)
    ok_a = resid < 1.0e-3
    print(f"  (a) finite-GBW SK -> ideal as ft -> inf : peak {p_inf:.6f} vs {p0:.6f} Hz, "
          f"|d| = {resid:.2e} Hz  {'PASS' if ok_a else 'FAIL'}")
    print("      Without this the AF2 sweep would be measuring a transcription error, not an op-amp.")
    if not ok_a:
        fail.append("AF1a")

    # (b) inherited: AB1's own known answer, re-asserted here so this gate can be run alone.
    ok_b = abs(p0 - AB.S125_PEAK_HZ) < 1.0
    ok_b = ok_b and (AB.S125_NOTCH_LO <= n0 <= AB.S125_NOTCH_HI)
    print(f"  (b) cascade reproduces s125 / GATE AB1   : peak {p0:.1f} Hz "
          f"(s125 {AB.S125_PEAK_HZ}), notch {n0:.1f} Hz "
          f"(W6 reads {AB.S125_NOTCH_LO:.0f}-{AB.S125_NOTCH_HI:.0f})  "
          f"{'PASS' if ok_b else 'FAIL'}")
    if not ok_b:
        fail.append("AF1b")

    # (c) the vertex law, checked in AF6 -- computed here, asserted there.
    i = int(np.argmin(np.abs(F - p0)))
    w = slice(i - 40, i + 41)
    curv = 2.0 * np.polyfit(L2[w] - L2[i], db_ideal[w], 2)[0]
    print(f"  (c) vertex curvature at the peak         : {curv:.3f} dB/oct^2 "
          f"(negative = a maximum)  {'PASS' if curv < 0 else 'FAIL'}")
    if curv >= 0:
        fail.append("AF1c")
    if fail:
        _die(f"{', '.join(fail)} — a known answer did not reproduce.")
    out["af1"] = dict(peak_hz=p0, notch_hz=n0, gbw_reduction_resid_hz=resid, curvature_db_oct2=curv)

    # ================= AF2  GAIN-BANDWIDTH =================================
    print("\n" + "-" * 96)
    print("AF2  CANDIDATE 1 — falling effective op-amp GBW  (s130's named carrier)")
    print("-" * 96)

    def dpeak_ft(lg):
        p, _ = peak_of(db_of(cascade_gbw(F, 10.0 ** lg)))
        return np.nan if p is None else p / p0 - 1.0

    # The sweep endpoints must be READABLE, or nothing below is.  That is a validity
    # question and it exits.  Whether a root exists INSIDE them is an outcome about the
    # candidate and must not (s108, and GATE P's own P5: "exit only on things that make
    # the numbers below meaningless" — a lever that cannot reach the target in DIRECTION
    # is the strongest possible refutation of it, not a malfunction).
    LG_LO, LG_HI = 3.5, 6.5
    if not (np.isfinite(dpeak_ft(LG_LO)) and np.isfinite(dpeak_ft(LG_HI))):
        _die("AF2 — the finite-GBW sweep lost the peak at one of its endpoints, so the "
             "bracket cannot be read at all.")
    try:
        ft_req = 10.0 ** brentq(lambda lg: dpeak_ft(lg) - TGT_PEAK, LG_LO, LG_HI, xtol=1e-9)
        unreachable = False
    except (ValueError, RuntimeError):
        ft_req, unreachable = None, True

    d_at_real = dpeak_ft(math.log10(TL07X_GBW_MIN))
    short_typ = 0.0 if unreachable else TL07X_GBW_TYP / ft_req
    short_min = 0.0 if unreachable else TL07X_GBW_MIN / ft_req

    print("     ft (Hz)      peak Hz     d(peak) %")
    sweep = [TL07X_GBW_TYP, TL07X_GBW_MIN, 1e6, 3e5, 1e5, 3e4, 1e4]
    if ft_req is not None:
        sweep.append(ft_req)
    for ft in sorted(sweep, reverse=True):
        p, _ = peak_of(db_of(cascade_gbw(F, ft)))
        tag = ""
        if ft_req is not None and abs(ft - ft_req) < 1.0:
            tag = "  <- REQUIRED"
        if abs(ft - TL07X_GBW_MIN) < 1.0:
            tag = "  <- TL07x min spec"
        print(f"    {ft:9.4g}   {p:9.1f}     {100*(p/p0-1):+8.2f}{tag}")

    if unreachable:
        print(f"\n  ⛔⛔ NO gain-bandwidth in [{10**LG_LO/1e3:.1f} kHz, {10**LG_HI/1e6:.1f} MHz]")
        print(f"      moves the peak by {100*TGT_PEAK:+.2f} % AT ALL — the lever cannot reach the")
        print( "      target in DIRECTION, which refutes it more strongly than any size argument.")
        print( "      (Lowering an op-amp's bandwidth can only move this vertex DOWN in frequency.)")
        out["af2"] = dict(ft_required_hz=None, unreachable_in_direction=True,
                          shortfall_typ=0.0, shortfall_min=0.0,
                          dpeak_at_min_spec=d_at_real, reaches=False)
        gbw_reaches = False
        print(f"\n  ⭐ FREE BY-PRODUCT: the model's IDEAL-op-amp assumption is costing "
              f"{abs(100*d_at_real):.3f} % at this feature.")
    else:
        print(f"\n  REQUIRED gain-bandwidth      : {ft_req/1e3:.2f} kHz")
        print(f"  TL07x published              : {TL07X_GBW_TYP/1e6:.2f} MHz typ, "
              f"{TL07X_GBW_MIN/1e6:.2f} MHz min")
        print(f"  SHORTFALL                    : {short_min:.0f}x even at the MINIMUM-spec part "
              f"({short_typ:.0f}x at typ)")
        print(f"  effect at the real GBW       : {100*d_at_real:+.3f} %  "
              f"against the {100*TGT_PEAK:+.2f} % required")

        gbw_reaches = short_min <= 1.0
        if gbw_reaches:
            print(f"\n  ⚠ REACHES ON SIZE: the required GBW ({ft_req/1e3:.2f} kHz) is at or "
                  f"above the part's own\n     published minimum, so size alone does not "
                  f"refute this candidate.")
        else:
            print(f"\n  ⛔ REFUTED ON SIZE: the required GBW is {short_min:.0f}x below the "
                  f"worst part TI ships.")
        print(f"\n  ⭐ FREE BY-PRODUCT: the model's IDEAL-op-amp assumption is costing "
              f"{abs(100*d_at_real):.3f} % at")
        print("     this feature — so it is not a hidden STATIC error here either, and nothing")
        print("     is owed to modelling the SK op-amps' finite bandwidth.")
        out["af2"] = dict(ft_required_hz=ft_req, unreachable_in_direction=False,
                          shortfall_typ=short_typ, shortfall_min=short_min,
                          dpeak_at_min_spec=d_at_real, reaches=bool(gbw_reaches))

    print("\n  ⛔⛔ AND REFUTED AGAIN, STRUCTURALLY, WHICH IS THE STRONGER HALF — this one")
    print("      holds however the size arithmetic above comes out:")
    print("      gain-bandwidth is a SMALL-SIGNAL parameter.  An op-amp in its linear region")
    print("      does not lose gain-bandwidth as the signal grows — the large-signal limit is")
    print("      SLEW (AF3), which is a rate limit and not a bandwidth reduction.  So there is")
    print("      no amplitude at which this lever moves AT ALL, and the size question is moot.")
    print("      s130's 'obvious single physical cause' names a mechanism that does not exist.")

    # ================= AF3  SLEW RATE ======================================
    print("\n" + "-" * 96)
    print("AF3  CANDIDATE 2 — slew-rate limiting in the SK op-amps")
    print("-" * 96)
    print("  The harshest thing the clipper can hand the SK pair is a FULL-RAIL SQUARE WAVE, so")
    print("  this is an upper bound over the whole audio band, not a sample of one signal.")
    print(f"  Rails read from FitParams.h: railNeg {RAIL_NEG:.2f} V, railPos {RAIL_POS:.2f} V.\n")

    n_h = np.arange(1, 2001, 2)
    print("     f0 Hz    after SK-B (V/us)   after SK-A (V/us)")
    worst = 0.0
    slew_rows = []
    for f0 in (100, 250, 500, 1000, 2000, 3000, 5000, 8000, 12000):
        fn = n_h * f0
        an = 4.0 * RAIL_MAX / (np.pi * n_h)
        hB = sk_ideal(fn, **AB.SK_B)
        hA = hB * sk_ideal(fn, **AB.SK_A)
        t = np.linspace(0.0, 1.0 / f0, 20001)

        def maxrate(H):
            y = np.zeros_like(t)
            for fi, ai, Hi in zip(fn, an, H):
                y += np.real(ai * Hi * np.exp(2j * np.pi * fi * t))
            return float(np.max(np.abs(np.gradient(y, t))) / 1e6)

        rB, rA = maxrate(hB), maxrate(hA)
        worst = max(worst, rB, rA)
        slew_rows.append(dict(f0=f0, sk_b=rB, sk_a=rA))
        print(f"    {f0:6d}    {rB:14.4f}    {rA:14.4f}")

    margin_min = TL07X_SR_MIN / worst
    print(f"\n  WORST |dV/dt| anywhere       : {worst:.3f} V/us")
    print(f"  TL07x published slew rate    : {TL07X_SR_TYP:.0f} V/us typ, {TL07X_SR_MIN:.0f} V/us min")
    print(f"  MARGIN                       : {margin_min:.0f}x even at the MINIMUM-spec part")
    slew_reaches = margin_min <= 1.0
    if slew_reaches:
        print(f"\n  ⚠ REACHES: the worst-case rate is at or above the part's own slew rate, so")
        print("     slew limiting IS engaged and must be modelled before it can be dismissed.")
    else:
        print(f"\n  ⛔ REFUTED: the op-amps never come within {margin_min:.0f}x of slewing, at any")
        print("     frequency, on the loudest waveform this chain can produce.  Slew limiting is")
        print("     not a lever here — it is not even engaged.")
    out["af3"] = dict(worst_v_per_us=worst, margin_min_spec=margin_min,
                      reaches=bool(slew_reaches), rows=slew_rows)

    # ================= AF4  THE RAIL CLAMP WE ALREADY SHIP =================
    print("\n" + "-" * 96)
    print("AF4  CANDIDATE 3 — output rail clamping  (ALREADY IN THE MODEL, already measured)")
    print("-" * 96)
    print(f"  FitParams.h railEnabled = {str(RAIL_ENABLED).lower()}  -> the shipped build "
          f"carries a\n  RailClamp on BOTH Sallen-Key outputs (PedalChain: skB, skA), and on five")
    print("  further op-amp outputs downstream of them.")
    if not RAIL_ENABLED:
        _die("AF4 — railEnabled is false in FitParams.h, so the empirical answer below is "
             "about a build we do not ship.  Re-read GATE W6 against the shipped fit.")

    if not os.path.exists(W_REPORT):
        _die(f"AF4 — {os.path.basename(W_REPORT)} is absent; GATE W6's measurement cannot be "
             "read and this sub-gate will not transcribe it from a handover.")
    w6 = json.load(open(W_REPORT)).get("w6", {}).get("treble_peak", {}).get("model", {})
    span = w6.get("span_frac")
    verdict = w6.get("verdict")
    if span is None or verdict is None:
        _die("AF4 — the stored GATE W report has no w6.treble_peak.model span; refusing.")
    print(f"\n  ⭐ THE EMPIRICAL ANSWER IS ALREADY ON DISK, and it is stronger than any")
    print("     calculation this gate could make.  GATE W6 measured the SHIPPED model's treble")
    print(f"     peak across the 24 dB stimulus ladder, with those clamps enabled:")
    print(f"\n       model treble_peak span = {100*span:.2f} %   verdict = {verdict}")
    print(f"       target                 = {abs(100*TGT_PEAK):.2f} %")
    reach4 = abs(span) >= abs(TGT_PEAK)
    if reach4:
        print(f"\n  ⚠ REACHES: the shipped clamps already move this peak {100*span:.2f} %, i.e. at")
        print("     or beyond the target — so this feature is NOT pinned by them and the whole")
        print("     framing of item 6's treble half needs re-reading against W6 before anything")
        print("     is built.")
    else:
        print(f"\n  ⛔ REFUTED: every post-clipper amplitude nonlinearity the model ALREADY HAS,")
        print(f"     acting together, moves this peak {100*span:.2f} % — "
              f"{abs(TGT_PEAK)/max(abs(span),1e-9):.0f}x short of the target.")
        print("     ⇒ the question is not 'add a post-clipper nonlinearity'.  We have seven of")
        print("     them and they do not move this feature.  A saturating clamp is the wrong")
        print("     SHAPE, not merely the wrong size: it compresses the fundamental almost")
        print("     uniformly across frequency, and a uniform gain change cannot move a vertex")
        print("     (GATE AB2's control).")
    out["af4"] = dict(rail_enabled=RAIL_ENABLED, w6_model_span_frac=span,
                      w6_verdict=verdict, reaches=bool(reach4))

    # ================= AF5  PARASITIC CEILINGS =============================
    print("\n" + "-" * 96)
    print("AF5  CANDIDATES 4-5 — parasitic capacitance, as CEILINGS")
    print("-" * 96)
    print("  These two cannot be measured here, so they are bounded instead: a ceiling is enough")
    print("  to refute when the requirement is a 10 % move.\n")

    # (4) op-amp input capacitance adds to C2 (the to-GND cap, which sets Q and w0).
    cin = TL07X_CIN_PF * 1e-12
    frac_b = cin / AB.SK_B["C2"]
    frac_a = cin / AB.SK_A["C2"]
    p_cin, _ = peak_of(db_of(cascade_gbw(F, 1.0e12, c2_extra=cin)))
    d_cin = p_cin / p0 - 1.0
    print(f"  (4) op-amp input capacitance ~{TL07X_CIN_PF:.0f} pF in parallel with C2")
    print(f"      = {100*frac_b:.2f} % of SK-B's C2 and {100*frac_a:.2f} % of SK-A's.")
    print(f"      Adding ALL of it (an absolute ceiling — it cannot be more than fully present)")
    print(f"      moves the peak {100*d_cin:+.3f} %, i.e. {abs(TGT_PEAK/d_cin):.0f}x short.  And a")
    print(f"      parasitic that is always present is not drive-DEPENDENT in the first place.")

    # (5) film-cap voltage coefficient.
    dc_frac = FILM_VCOEF_PER_V * RAIL_MAX
    p_vc, _ = peak_of(db_of(AB.cascade(F, sk_scale=1.0 + dc_frac)))
    d_vc = p_vc / p0 - 1.0
    print(f"\n  (5) film-cap voltage coefficient, ceiling {1e2*FILM_VCOEF_PER_V:.1f} %/V over a")
    print(f"      {RAIL_MAX:.1f} V swing = {100*dc_frac:.2f} % of C.  Applied to BOTH SK stages")
    print(f"      that moves the peak {100*d_vc:+.3f} %, {abs(TGT_PEAK/d_vc):.0f}x short.")
    print(f"      (C18/C19/C20/C27 are 1n-2n2 film parts per the BOM; a class-2 ceramic would")
    print(f"      be worse-behaved, but it is not what the board specifies.)")
    out["af5"] = dict(dpeak_input_cap=d_cin, dpeak_film_vcoef=d_vc,
                      cin_frac_skb=frac_b, cin_frac_ska=frac_a)

    # ================= AF6  THE REFRAME ====================================
    print("\n" + "-" * 96)
    print("AF6  THE REFRAME — a vertex moves under a SLOPE change, with no corner moving")
    print("-" * 96)
    print("  AB4 established that this peak is a VERTEX: the bridged-T's rise meeting three")
    print("  rolloffs.  A vertex sits where the total slope crosses zero, so ANY drive-dependent")
    print("  TILT across its neighbourhood moves it — no corner has to move at all, and every")
    print("  refutation above is about corners.\n")

    need_oct = math.log2(1.0 + TGT_PEAK)

    def tilted(T):
        return db_ideal + T * (L2 - math.log2(p0))

    def dpeak_T(T):
        p, _ = peak_of(tilted(T))
        return np.nan if p is None else p / p0 - 1.0

    try:
        T_req = brentq(lambda T: dpeak_T(T) - TGT_PEAK, -4.0, 4.0, xtol=1e-10)
    except (ValueError, RuntimeError):
        _die("AF6 — no tilt in +-4 dB/oct reaches the target; the vertex is leaving the window.")

    T_pred = -curv * need_oct
    agree = abs(T_req - T_pred) / abs(T_req)
    ok_c = agree < 0.10
    print(f"  AF1c's vertex law   dx = -T / C , with C = {curv:.3f} dB/oct^2 and "
          f"dx = {need_oct:+.4f} oct")
    print(f"    PREDICTED tilt : {T_pred:+.3f} dB/oct")
    print(f"    MEASURED tilt  : {T_req:+.3f} dB/oct   (relocating the vertex on the tilted curve)")
    print(f"    agreement      : {100*agree:.1f} %   {'PASS' if ok_c else 'FAIL'}")
    print("    ⇒ this is AF1's third known answer, and it is the one that certifies the REFRAME:")
    print("      the requirement really is a local slope, derivable from the curvature alone.")
    if not ok_c:
        fail.append("AF1c/AF6")

    p_chk, _ = peak_of(tilted(T_req))
    n_chk, _ = notch_of(tilted(T_req))
    d_notch_T = n_chk / n0 - 1.0
    oct_band = math.log2(8000.0 / 100.0)
    print(f"\n  THE SIZED REQUIREMENT: a drive-dependent slope change of {T_req:+.3f} dB/oct")
    print(f"  in the neighbourhood of {p0:.0f} Hz moves the peak {100*dpeak_T(T_req):+.2f} % "
          f"(target {100*TGT_PEAK:+.2f} %).")
    print(f"\n  ⚠ THAT IS A LOCAL NUMBER.  The curvature argument is strictly local, so what is")
    print(f"    required is a slope change AT THE VERTEX.  Extrapolating it to a broadband tilt")
    print(f"    is an ASSUMPTION, flagged rather than hidden:")
    print(f"      if broadband, {T_req*oct_band:+.2f} dB end-to-end over 100 Hz-8 kHz "
          f"({oct_band:.2f} oct)")
    print(f"      a linear tilt of that span has rms {abs(T_req*oct_band)/(2*math.sqrt(3)):.2f} dB")
    print(f"      GATE Q's measured D(f) — the drive-dependent half of the OD-path deficit,")
    print(f"      whose own source says 'only a nonlinearity can carry it' — is 3.01 dB rms.")
    q_rms = 3.01
    frac_of_q = (abs(T_req * oct_band) / (2 * math.sqrt(3))) / q_rms
    print(f"      ⇒ the requirement is {100*frac_of_q:.0f} % of a term this project has ALREADY")
    print(f"        MEASURED.  The SIZE is available.  ⚠ Whether the SHAPE matches is unmeasured:")
    print(f"        an rms says nothing about whether D(f) is a monotone tilt at 2.9 kHz.")

    print(f"\n  AND THE CROSS-CHECK THAT KEEPS THIS HONEST: the same tilt moves the NOTCH")
    print(f"    {n0:.1f} -> {n_chk:.1f} Hz ({100*d_notch_T:+.2f} %) against a "
          f"{100*TGT_NOTCH:+.2f} % target.")
    print(f"    ⇒ the tilt is a PEAK-ONLY lever, exactly as the SK axis is — it independently")
    print("      reproduces AB3's orthogonality from a third construction, and it does NOT")
    print("      collapse AB6's two sub-targets into one.  The bridged-T half stays unowned.")
    out["af6"] = dict(tilt_required_db_oct=T_req, tilt_predicted_db_oct=T_pred,
                      agreement=agree, dnotch_under_tilt=d_notch_T,
                      broadband_db=T_req * oct_band, frac_of_gateq_dfn=frac_of_q,
                      peak_hz_after=p_chk)

    # ================= AF7  VERDICT ========================================
    print("\n" + "-" * 96)
    print("AF7  VERDICT — computed per candidate, as a COMPARISON against the target")
    print("-" * 96)
    # `reach` is "how far this candidate gets, where 1.0 is exactly enough".  A candidate
    # that cannot reach the target in DIRECTION at any parameter value scores 0.0 — the
    # AF2 branch above sets short_min = 0 for exactly that case, so guard the reciprocal
    # rather than letting an honest zero become a ZeroDivisionError.
    cands = [
        ("falling op-amp GBW", (1.0 / short_min) if short_min > 0.0 else 0.0, gbw_reaches,
         "and structurally impossible: GBW is small-signal"),
        ("slew-rate limiting", 1.0 / margin_min, slew_reaches,
         "never engages at any frequency"),
        ("output rail clamping", abs(span) / abs(TGT_PEAK), reach4,
         "already shipped; W6 measures the result"),
        ("op-amp input capacitance", abs(d_cin / TGT_PEAK), abs(d_cin) >= abs(TGT_PEAK),
         "and not drive-dependent"),
        ("film-cap voltage coefficient", abs(d_vc / TGT_PEAK), abs(d_vc) >= abs(TGT_PEAK),
         "ceiling, generous"),
    ]
    print(f"  {'candidate':<30} {'reach (1.0 = exactly enough)':>30}   verdict")
    admissible, refuted = [], []
    for name, reach, ok, note in cands:
        (admissible if ok else refuted).append(name)
        print(f"  {name:<30} {reach:>30.4g}   {'REACHES' if ok else 'REFUTED'}  ({note})")
    print(f"\n  AF7-MEMBERSHIP reaches={sorted(admissible)} refuted={sorted(refuted)}")

    print("\n  ⭐⭐ THE DELIVERABLE, in one line:")
    if not admissible:
        print("     NO physical mechanism screened here can move the two Sallen-Key CORNERS by")
        print("     the required 10 %.  The SK-bandwidth frame is refuted as a MECHANISM while")
        print("     AB6's ARITHMETIC stands — 'SK tau x 1.1113' remains a correct SIZING of the")
        print("     peak's required move, and is not a description of anything the circuit does.")
        print(f"\n     What survives, sized: a drive-dependent SLOPE change of {T_req:+.3f} dB/oct")
        print(f"     at {p0:.0f} Hz, which moves the vertex without moving any corner, and which")
        print(f"     is {100*frac_of_q:.0f} % of GATE Q's already-measured D(f).  That is a")
        print("     FREQUENCY-DEPENDENT COMPRESSION target — the class item 6 has pointed at")
        print("     since s125 — and it lives AT OR UPSTREAM OF the clipper, not in the SK pair.")
    else:
        print(f"     {', '.join(admissible)} reaches the target and should be built.")
    out["af7"] = dict(admissible=sorted(admissible), refuted=sorted(refuted))

    print("\n" + "=" * 96)
    if fail:
        print(f"GATE AF: REFUSED — {', '.join(fail)} did not pass.  Nothing above them is quotable.")
    else:
        print("GATE AF: all guards passed.  AF2-AF7 are readable.")
    print("=" * 96)

    if args.json:
        os.makedirs(os.path.dirname(os.path.abspath(args.json)), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"wrote {args.json}")
    sys.exit(1 if fail else 0)


if __name__ == "__main__":
    main()
