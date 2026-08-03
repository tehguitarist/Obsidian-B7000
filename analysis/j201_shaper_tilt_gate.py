#!/usr/bin/env python3
"""GATE AK — THE J201's OWN SHAPER AS A **TILT** MECHANISM FOR ITEM 6's TREBLE HALF.

Session 139 (GATE AJ) refuted the J201's **gate capacitance** and closed with the claim that
"every named carrier on both sides of the clipper is now refuted".  Its own `NEXT` #1(b) names
the exception: the J201's **shaper** — the one pre-clipper nonlinearity nobody has screened *as
a tilt mechanism*, as opposed to as a harmonic one.  A capacitance and a transconductance are
different carriers; this gate screens the second.

WHAT ITEM 6 NEEDS (read from stored reports, never transcribed): a drive-dependent slope change
at the ~2935 Hz vertex, worth AH7's budget, that STEEPENS with frequency (AG4).

THE STAGE, from JfetStage.h's own class note (it is a CURRENT source, not a voltage source):

    k(s)    = 1 + gm*Zs(s),   Zs = R6 || C3     degeneration factor, 1+gm*R6 at DC -> 1 at HF
    Gm(s)   = gm / k(s)                          transconductance RISES with frequency
    Rout(s) = ro * k(s)                          drain output R FALLS with frequency
    => open-circuit gain Gm*Rout = gm*ro         FLAT, independent of the degeneration

so the shelf appears ONLY to the extent the stage is LOADED, and the drain-node block is

    T(f, gm) = Gm(f) * ( Zout(f, gm) || Zin_ladder(f) ),   Zout = [ro*k(s)] || rq2

THREE ROUTES, and this gate screens all three:

  1. the shaper AS SHIPPED — memoryless, sitting between the 1/k(s) shelf and the *(-gm)
     scaling.  A memoryless map's incremental gain at a given amplitude is a SCALAR, so
     log-magnitude gains a constant and the tilt is unchanged EXACTLY.  (AB2's own control:
     a uniform gain change cannot move a vertex.)
  2. gm SAG through k(s) — the nonlinear-degeneration coupling the shipped Wiener-Hammerstein
     model omits (JfetStage.h says so in as many words: "the true degeneration is nonlinear
     feedback, vgs = vg - i_d*Zs, an implicit solve").  gm scales rp = ro*gm*R6 in the drain
     impedance, which MOVES A POLE — a real tilt mechanism, and the one worth sizing.
  3. amplitude-dependent compression — the shaper is memoryless but sits DOWNSTREAM of the
     frequency-dependent shelf, so it sees a frequency-dependent drive and therefore compresses
     by different amounts at different frequencies.  Route 2 does not model this.

WHY NO RENDER (AI1c's licence, re-asserted here on THIS gate's blocks): the graded quantity is
a tilt CHANGE, the tilt operator is LINEAR on log-magnitude, so every gm-independent block —
the treble ladder, IC2_A, the clipper, the bridged-T, both Sallen-Keys — contributes the same
slope at both ends of the ladder and cancels EXACTLY.  Only the drain-node block varies.

⚠ SCOPE.  This is about the TILT AT THE VERTEX.  It says nothing about the J201's even-order
harmonic role (`reference-sources.md` §4), which is a separate and still-live item, and nothing
about the bridged-T half of AB6.
"""
import argparse
import contextlib
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import at_clipper_tilt_gate as AI       # noqa: E402  FINE, tilt_fine, h_at, grunt_caps
import bt_pair_shape_gate as AB         # noqa: E402  _read_fitparam, R16/R18/C14
import pre_clipper_tilt_gate as AJ      # noqa: E402  ladder_zin, J_R4/R5/C2/R6/C3

with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ           # noqa: E402  jfet_source_z, treble_attack_tf

AG_REPORT = "analysis/reports/s135_drive_tilt.json"
AH_REPORT = "analysis/reports/s137_vertex_curvature.json"
AI_REPORT = "analysis/reports/s138_at_clipper_tilt.json"
OUT_JSON = "analysis/reports/s140_j201_shaper_tilt.json"

# --- J201 source-degeneration network, schematic-verified (JfetStage.h kR6/kC3) -------------
J_R6, J_C3 = AJ.J_R6, AJ.J_C3

# --- gm sag fractions.  The mechanism's own direction is a REDUCTION (the shaper compresses,
# so the incremental transconductance FALLS with drive).  -99 % is quoted as a LIMIT, and the
# gate additionally evaluates gm -> 0, at which a JFET is not an amplifier at all.
GM_SAG_FRACS = (-0.001, -0.01, -0.10, -0.50, -0.90, -0.99)
GM_LIMIT_FACTOR = 1.0e-6

KA_TOL_DB = 1e-6
KA_TOL_TILT = 1e-9
KA_TOL_REL = 1e-9
KA_TOL_FLAT = 1e-9        # AK1d — Gm*Rout = gm*ro is exact algebra

SINGLE_POLE_EXPONENT_BOUND = AJ.SINGLE_POLE_EXPONENT_BOUND


def _die(msg):
    print(f"\n⛔ GATE AK REFUSES: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# The blocks
# ---------------------------------------------------------------------------
def _consts():
    return (AB._read_fitparam("jfetGm"), AB._read_fitparam("jfetRo"),
            AB._read_fitparam("jfetRq2"))


def k_of_s(f, gm):
    """Degeneration factor k = 1 + gm*Zs,  Zs = R6 || C3."""
    s = 2j * np.pi * np.asarray(f, dtype=float)
    zs = 1.0 / (1.0 / J_R6 + s * J_C3)
    return 1.0 + gm * zs


def shelf_db(f, gm):
    """The 1/k(s) shelf — the effective-vgs filter the shaper is driven through."""
    return 20.0 * np.log10(np.abs(1.0 / k_of_s(f, gm)))


def bare_drain_db(f, gm, ro):
    """Gm*Rout for the BARE device (no active load, no ladder) — must be flat at gm*ro."""
    return 20.0 * np.log10(np.abs((gm / k_of_s(f, gm)) * (ro * k_of_s(f, gm))))


def drain_db(gm, ro, rq2, zin, f=None):
    """The gm-dependent block:  T = Gm(f) * ( Zout(f, gm) || Zin(f) ).

    Everything downstream of the drain node is gm-independent and cancels from the tilt CHANGE
    by AK1a's licence, so it is deliberately NOT modelled here.
    """
    f = AI.FINE if f is None else f
    gmf = gm / k_of_s(f, gm)
    zout = EQ.jfet_source_z(f, gm=gm, ro=ro, Rq2=rq2, R6=J_R6, C3=J_C3)
    zd = 1.0 / (1.0 / zout + 1.0 / zin)
    return 20.0 * np.log10(np.abs(gmf * zd))


# ---------------------------------------------------------------------------
# AK1 — known answers
# ---------------------------------------------------------------------------
def gate_ak1(f0, half, gm, ro, rq2, zin, out):
    print("\n" + "-" * 96)
    print("AK1  KNOWN ANSWERS")
    print("-" * 96)

    # (a) THE LICENCE, re-asserted on THIS gate's blocks (AI1c / AJ1a).
    s = 2j * np.pi * AI.FINE
    fixed = (1.0 + s / (2 * np.pi * 2500.0)) / (
        (1.0 + s / (2 * np.pi * 900.0)) * (1.0 + s / (2 * np.pi * 3300.0)) ** 2)
    fdb = 20.0 * np.log10(np.abs(fixed))
    a_db = drain_db(gm, ro, rq2, zin)
    b_db = drain_db(0.5 * gm, ro, rq2, zin)
    bare = AI.tilt_fine(b_db, f0, half) - AI.tilt_fine(a_db, f0, half)
    withf = AI.tilt_fine(b_db + fdb, f0, half) - AI.tilt_fine(a_db + fdb, f0, half)
    cancel = abs(withf - bare)
    print(f"  (a) LICENCE — a wild gm-independent block cancels from the tilt CHANGE : "
          f"{cancel:.3e} dB/oct (bar {KA_TOL_TILT:g})")
    if cancel > KA_TOL_TILT:
        _die(f"AK1a — a gm-independent block did NOT cancel ({cancel:.3e} dB/oct).  The whole "
             f"no-render simplification is invalid; do not read AK2-AK5.")

    # (b) injected-tilt recovery.  T = 0 is its own control (s133).
    inj = 0.0
    for T in (0.0, -1.199, +3.0):
        got = (AI.tilt_fine(a_db + T * np.log2(AI.FINE / f0), f0, half)
               - AI.tilt_fine(a_db, f0, half))
        inj = max(inj, abs(got - T))
    print(f"  (b) injected-tilt recovery over T = 0 / -1.199 / +3 : worst {inj:.3e} dB/oct "
          f"(bar {KA_TOL_TILT:g})")
    if inj > KA_TOL_TILT:
        _die(f"AK1b — the tilt estimator does not recover an injected tilt ({inj:.3e}).")

    # (c) jfet_source_z IS the network this gate assumes:  [ro + rp/(1+s R6 C3)] || rq2,
    #     rp = ro*gm*R6.  Compared POINTWISE over the whole grid, which is exact algebra.
    #     ⚠ A first draft compared against the two ASYMPTOTES (ro+rp)||rq2 and ro||rq2 and
    #     failed at 1.6e-8 against correct code: at 1 MHz the shelf term rp/(1+sR6C3) is still
    #     14.5 ohm, not 0, so the bar sat below the asymptote's own truncation error — `a
    #     tolerance a correct implementation cannot meet is a broken test` (s123).  The repair
    #     is to make the check EXACT and therefore STRICTER (the whole curve, not two points),
    #     never to loosen the bar.
    rp = ro * gm * J_R6
    s_f = 2j * np.pi * AI.FINE
    pred = 1.0 / (1.0 / (ro + rp / (1.0 + s_f * J_R6 * J_C3)) + 1.0 / rq2)
    got = EQ.jfet_source_z(AI.FINE, gm=gm, ro=ro, Rq2=rq2, R6=J_R6, C3=J_C3)
    rel_z = float(np.max(np.abs(got - pred) / np.abs(pred)))
    lf = float(np.abs(EQ.jfet_source_z(1.0e-3, gm=gm, ro=ro, Rq2=rq2, R6=J_R6, C3=J_C3)))
    hf = float(np.abs(EQ.jfet_source_z(1.0e6, gm=gm, ro=ro, Rq2=rq2, R6=J_R6, C3=J_C3)))
    print(f"  (c) jfet_source_z vs [ro + rp/(1+sR6C3)] || rq2,  rp = ro*gm*R6 = {rp / 1e3:.1f}k")
    print(f"        pointwise over {AI.FINE.size} bins : worst rel {rel_z:.3e} "
          f"(bar {KA_TOL_REL:g})")
    print(f"        asymptotes, for reading only : LF {lf / 1e3:.3f}k   HF {hf / 1e3:.3f}k")
    if rel_z > KA_TOL_REL:
        _die(f"AK1c — jfet_source_z is not the network this gate assumes ({rel_z:.3e}); every "
             f"number below is built on the wrong drain impedance.")

    # (d) the structural identity JfetStage.h rests on: Gm*Rout = gm*ro, FLAT, at every gm.
    #     ⚠ It holds for the BARE DEVICE only.  The shipped Zout also shunts rq2, and
    #     Gm*(ro*k || rq2) = gm*ro*rq2/(ro*k + rq2) keeps k(s) in the denominator — so a draft
    #     that asserted this WITH rq2 in circuit failed at 3.9e-3 dB/oct against correct code
    #     (`a tolerance a correct implementation cannot meet is a broken test`, s123).
    flat = max(abs(AI.tilt_fine(bare_drain_db(AI.FINE, g, ro), f0, half))
               for g in (gm, 0.5 * gm, 0.1 * gm))
    print(f"  (d) BARE-device Gm*Rout = gm*ro is flat at gm, gm/2, gm/10 : worst "
          f"{flat:.3e} dB/oct (bar {KA_TOL_FLAT:g})")
    if flat > KA_TOL_FLAT:
        _die(f"AK1d — Gm*Rout is not flat ({flat:.3e} dB/oct), so this gate's model of the stage "
             f"contradicts JfetStage.h's own class note.  One of the two is wrong.")
    inf = np.full_like(AI.FINE, 1.0e15)
    rq_only = max(abs(AI.tilt_fine(drain_db(g, ro, rq2, inf), f0, half))
                  for g in (gm, 0.5 * gm, 0.1 * gm))
    print(f"      and what the ACTIVE LOAD alone contributes (no ladder) : {rq_only:.3e} dB/oct")
    print(f"      -> the shelf appears ONLY through loading, exactly as JfetStage.h claims.")

    # (e) the ladder input impedance, two independent probe impedances (AJ1d, re-asserted
    #     because this gate's Z_drain is built on it).
    z1 = AJ.ladder_zin(AI.FINE, zs_probe=1.0e3)
    z2 = AJ.ladder_zin(AI.FINE, zs_probe=47.0e3)
    rel = float(np.max(np.abs(z1 - z2) / np.abs(z1)))
    print(f"  (e) ladder Zin from two probe impedances (1k, 47k) : worst rel {rel:.3e} "
          f"(bar {KA_TOL_REL:g})")
    if rel > KA_TOL_REL:
        _die(f"AK1e — the ladder input impedance is probe-dependent ({rel:.3e}), so Z_drain is "
             f"not a measurement.")

    out["ak1"] = {"cancel": cancel, "inject_worst": inj, "zsrc_rel": rel_z,
                  "bare_flat": flat, "rq2_only": rq_only, "zin_rel": rel, "rp_ohm": rp}


# ---------------------------------------------------------------------------
# AK2 — route 1: the shaper AS SHIPPED
# ---------------------------------------------------------------------------
def gate_ak2(f0, half, gm, ro, rq2, zin, budget, out):
    print("\n" + "-" * 96)
    print("AK2  ROUTE 1 — the shaper AS SHIPPED (memoryless, between the shelf and *(-gm))")
    print("-" * 96)
    print("  A memoryless map's incremental gain at a given amplitude is a SCALAR multiplying")
    print("  the drain current, so log-magnitude gains a CONSTANT and the tilt is unchanged.")
    print("  Asserted rather than argued (AI1c's discipline), over compressions from -0.1 dB")
    print("  to a 40 dB squash:")
    base = drain_db(gm, ro, rq2, zin)
    t0 = AI.tilt_fine(base, f0, half)
    worst = 0.0
    for g_db in (-0.1, -1.0, -6.0, -20.0, -40.0):
        d = abs(AI.tilt_fine(base + g_db, f0, half) - t0)
        worst = max(worst, d)
        print(f"      shaper gain {g_db:+6.1f} dB   ->   d(tilt) {d:.3e} dB/oct")
    reach = abs(worst / budget) if budget else 0.0
    print(f"\n  worst d(tilt) {worst:.3e} dB/oct = {100 * reach:.4f}% of AH7's budget "
          f"{budget:+.3f}")
    if worst > KA_TOL_TILT:
        verdict = ("REACHES — a uniform gain change moved the vertex tilt, which contradicts "
                   "AB2's control; the model is wrong, not the candidate")
        print(f"\n  ⚠ ROUTE 1 IS NOT INERT ({worst:.3e} dB/oct) — that contradicts AB2 and this")
        print(f"    gate's own premise.  Read AK3-AK4 only after resolving it.")
    else:
        verdict = ("REFUTED STRUCTURALLY — a memoryless shaper is a pure gain change at the "
                   "fundamental, and a uniform gain change cannot move a vertex (AB2); the "
                   "tilt change is zero to machine precision, at any compression")
        print(f"\n  ⛔ ROUTE 1 REFUTED STRUCTURALLY — zero to machine precision at every")
        print(f"     compression, so the shipped shaper contributes NO tilt however hard it is")
        print(f"     driven.  This needs no size argument and no threshold.")
    out["ak2"] = {"worst_dtilt": worst, "reach": reach, "verdict": verdict}
    return {"name": "shaper_as_shipped", "reach": reach, "verdict": verdict,
            "refuted": worst <= KA_TOL_TILT}


# ---------------------------------------------------------------------------
# AK3 — route 2: gm sag through k(s)
# ---------------------------------------------------------------------------
def gate_ak3(f0, half, gm, ro, rq2, zin, budget, avail, ag4, out):
    print("\n" + "-" * 96)
    print("AK3  ROUTE 2 — gm SAG through k(s)  (the omitted nonlinear-degeneration coupling)")
    print("-" * 96)
    print("  gm scales rp = ro*gm*R6 in the drain impedance, so it MOVES A POLE — unlike route 1")
    print("  this is a genuine tilt mechanism.  The shaper compresses, so the mechanism's own")
    print("  direction is a REDUCTION in gm.")
    base = drain_db(gm, ro, rq2, zin)
    t0 = AI.tilt_fine(base, f0, half)
    print(f"\n  shipped drain-block tilt at the vertex : {t0:+.4f} dB/oct")
    print(f"\n  {'dgm/gm':>8s}  {'tilt':>9s}  {'d(tilt)':>11s}  {'reach vs budget':>16s}  "
          f"{'sign ok':>7s}")
    rows = []
    for frac in GM_SAG_FRACS:
        t = AI.tilt_fine(drain_db(gm * (1.0 + frac), ro, rq2, zin), f0, half)
        d = t - t0
        rows.append([frac, t, d])
        print(f"  {100 * frac:+7.1f}%  {t:+9.4f}  {d:+11.6f}  {100 * abs(d / budget):15.3f}%  "
              f"{str((d < 0) == (budget < 0)):>7s}")
    d_lim = AI.tilt_fine(drain_db(gm * GM_LIMIT_FACTOR, ro, rq2, zin), f0, half) - t0
    reach = abs(d_lim / budget) if budget else 0.0
    sign_ok = (d_lim < 0) == (budget < 0)
    print(f"\n  gm -> 0 (a LIMIT, not an operating point — a JFET with no transconductance is")
    print(f"  not an amplifier at all, so this ceiling holds for ANY sag):")
    print(f"      d(tilt) {d_lim:+.6f} dB/oct   =   {100 * reach:.3f}% of AH7's budget"
          f"   sign ok {sign_ok}")

    # ---- AK3b: SHAPE, against the deficit's own frequency dependence ----------------------
    print("\n  " + "." * 92)
    print("  AK3b  SHAPE — does the mechanism's tilt STEEPEN with frequency, as the deficit does?")
    print("  " + "." * 92)
    rows4 = [r for r in ag4["rows"] if r[3]]
    if len(rows4) < 3:
        _die(f"AK3b — AG4 reports {len(rows4)} uncontaminated centres, fewer than the 3 its own "
             f"finding rests on; the exponent cannot be estimated and this gate will not "
             f"substitute contaminated ones.")
    fs = np.array([r[0] for r in rows4])
    dfc = np.array([r[2] - r[1] for r in rows4])          # PEDAL - MODEL, AG4's own columns
    if np.any(dfc >= 0.0):
        _die("AK3b — a counted AG4 centre has a non-negative deficit, so log|D| is not the right "
             "statistic there; refusing rather than taking a log of a sign change.")
    def_pair = [float(np.log(abs(dfc[i + 1]) / abs(dfc[i])) / np.log(fs[i + 1] / fs[i]))
                for i in range(len(fs) - 1)]

    # the mechanism, at the SAME centres and the same estimator
    mech = np.array([abs(AI.tilt_fine(drain_db(0.5 * gm, ro, rq2, zin), c, half)
                         - AI.tilt_fine(base, c, half)) for c in fs])
    if np.any(mech <= 0.0):
        _die("AK3b — the mechanism's tilt change is zero at a counted centre, so its exponent is "
             "undefined; refusing rather than taking log(0).")
    mech_pair = [float(np.log(mech[i + 1] / mech[i]) / np.log(fs[i + 1] / fs[i]))
                 for i in range(len(fs) - 1)]
    print(f"  centres (Hz)                       : " + "  ".join(f"{f:9.1f}" for f in fs))
    print(f"  DEFICIT  |PEDAL-MODEL| (dB/oct)    : " + "  ".join(f"{abs(d):9.4f}" for d in dfc))
    print(f"  MECHANISM |d(tilt)| at gm/2        : " + "  ".join(f"{m:9.2e}" for m in mech))
    print(f"\n  deficit   adjacent-pair exponents  : "
          + "  ".join(f"{p:+.3f}" for p in def_pair) + f"   -> min {min(def_pair):+.3f}")
    print(f"  mechanism adjacent-pair exponents  : "
          + "  ".join(f"{p:+.3f}" for p in mech_pair) + f"   -> max {max(mech_pair):+.3f}")
    print(f"  (the exact bound for ONE moving pole is <= {SINGLE_POLE_EXPONENT_BOUND:+.3f})")
    # The threshold-free statement: the deficit RISES with frequency and the mechanism FALLS.
    shape_refuted = max(mech_pair) < 0.0 < min(def_pair)
    if shape_refuted:
        print(f"\n  ⛔ REFUTED ON SHAPE, WITH NO THRESHOLD — the deficit RISES with frequency and")
        print(f"     the mechanism FALLS.  It is not merely under the single-pole bound, it is on")
        print(f"     the wrong side of ZERO: strongest where the deficit is weakest, and dying by")
        print(f"     the vertex.")
    else:
        print(f"\n  ⚠ the mechanism's frequency dependence does NOT have the opposite sign to the")
        print(f"    deficit's, so the shape screen does not refute it and the verdict must rest")
        print(f"    on size alone.")
    print(f"  ⚠ n = {len(rows4)} centres (AG4's own membership).")

    if shape_refuted:
        verdict = (f"REFUTED ON SHAPE AND SIZE — the deficit RISES with frequency "
                   f"(f^{min(def_pair):+.2f} on the weakest pair) while the mechanism FALLS "
                   f"(f^{max(mech_pair):+.2f}), the opposite sign and so refuted with no "
                   f"threshold; and even at gm -> 0, a limit at which the stage has no gain "
                   f"left, it reaches {100 * reach:.2f}% of the budget")
    elif reach >= 1.0 and sign_ok:
        verdict = (f"REACHES — gm sag can carry {100 * reach:.1f}% of the budget with the right "
                   f"sign")
    else:
        verdict = (f"REFUTED ON SIZE — {100 * reach:.2f}% of the budget at gm -> 0, a limit at "
                   f"which the stage has no gain left")
    out["ak3"] = {"tilt_shipped": t0, "rows": rows, "d_limit": d_lim, "reach": reach,
                  "sign_ok": bool(sign_ok), "centres": fs.tolist(),
                  "deficit_pairs": def_pair, "mech_pairs": mech_pair,
                  "shape_refuted": bool(shape_refuted), "verdict": verdict}
    return {"name": "gm_sag", "reach": reach, "verdict": verdict,
            "refuted": shape_refuted or reach < 1.0 or not sign_ok}


# ---------------------------------------------------------------------------
# AK4 — route 3: amplitude-dependent compression through the shelf
# ---------------------------------------------------------------------------
def gate_ak4(f0, half, gm, budget, out):
    print("\n" + "-" * 96)
    print("AK4  ROUTE 3 — amplitude-dependent compression (the shaper sees the 1/k(s) shelf)")
    print("-" * 96)
    print("  The shaper is memoryless, but it is driven THROUGH the shelf, so the amplitude it")
    print("  sees is frequency-dependent and it compresses by different amounts across the")
    print("  window.  Route 2 does not model this.")
    print("\n  CLASS BOUND, no threshold and no shaper model: if the shaper's gain is G(A) and")
    print("  the amplitude it sees varies by d dB across the window, the gain varies by")
    print("  (dG_dB/dA_dB)*d, and for ANY compressor dG_dB/dA_dB lies in [-1, 0].  So the tilt")
    print("  this route can produce is bounded by the SHELF'S OWN VARIATION across the window,")
    print("  however extreme the nonlinearity.")
    lo, hi = f0 * 2.0 ** (-half), f0 * 2.0 ** (+half)
    d_lo, d_hi = float(shelf_db(lo, gm)), float(shelf_db(hi, gm))
    span = abs(d_hi - d_lo)
    per_oct = span / (2.0 * half)
    reach = abs(per_oct / budget) if budget else 0.0
    f_zero = 1.0 / (2 * np.pi * J_R6 * J_C3)
    f_pole = (1.0 + gm * J_R6) / (2 * np.pi * J_R6 * J_C3)
    print(f"\n  1/k(s) shelf across the window : {lo:.1f} Hz {d_lo:+.4f} dB   ->   "
          f"{hi:.1f} Hz {d_hi:+.4f} dB")
    print(f"  span {span:.4f} dB over {2 * half:.1f} oct   =>   bound {per_oct:.4f} dB/oct")
    print(f"  =  {100 * reach:.2f}% of AH7's budget, FOR ANY SHAPER SHAPE")
    print(f"\n  the shelf's corners:  zero 1/(2pi R6 C3) = {f_zero:.1f} Hz,"
          f"  pole (1+gm*R6)/(2pi R6 C3) = {f_pole:.1f} Hz")
    print(f"  both a decade below the {f0:.0f} Hz vertex — which is the COMMON ROOT CAUSE of all")
    print(f"  three routes: everything that acts through this shelf is spent before it reaches")
    print(f"  the feature.")
    if reach >= 1.0:
        verdict = (f"REACHES — the shelf varies enough across the window ({span:.3f} dB) for a "
                   f"downstream compressor to carry the budget")
        print(f"\n  ⚠ ROUTE 3 REACHES on the class bound; it needs a shaper model to size properly.")
    else:
        verdict = (f"REFUTED ON A CLASS BOUND — bounded by the shelf's own {span:.4f} dB "
                   f"variation across the window = {per_oct:.4f} dB/oct = {100 * reach:.2f}% of "
                   f"the budget, for ANY memoryless shaper however extreme")
        print(f"\n  ⛔ ROUTE 3 REFUTED ON A CLASS BOUND — and the bound is independent of the")
        print(f"     shaper, so no re-fit of s/a/ceiling can move it.")
    out["ak4"] = {"f_lo": lo, "f_hi": hi, "shelf_lo_db": d_lo, "shelf_hi_db": d_hi,
                  "span_db": span, "bound_db_oct": per_oct, "reach": reach,
                  "f_zero": f_zero, "f_pole": f_pole, "verdict": verdict}
    return {"name": "amplitude_compression", "reach": reach, "verdict": verdict,
            "refuted": reach < 1.0}


# ---------------------------------------------------------------------------
# AK5 — item 6's GRUNT-sign gate.  This candidate PASSES it, which is the point.
# ---------------------------------------------------------------------------
def gate_ak5(f0, half, gm, ro, rq2, zin, need, out):
    print("\n" + "-" * 96)
    print("AK5  ITEM 6's GRUNT-SIGN GATE — and this candidate PASSES it")
    print("-" * 96)
    print("  The J201 is UPSTREAM of the GRUNT switch and the tilt operator is linear on")
    print("  log-magnitude, so the J201 block's tilt change is added identically whichever cap")
    print("  is switched in.  Asserted, not argued — through AI's own at-clipper block at each")
    print("  SHIPPED cap (AI.grunt_caps(), which composes the ADD-caps as the stage does):")
    caps = AI.grunt_caps()
    base = drain_db(gm, ro, rq2, zin)
    sag = drain_db(0.5 * gm, ro, rq2, zin)
    per = {}
    for nm in ("cut", "flat", "boost"):
        gdb = AI.mech_db(AB.CLIP_A0, caps[nm])
        per[nm] = (AI.tilt_fine(sag + gdb, f0, half) - AI.tilt_fine(base + gdb, f0, half))
    spread = max(per.values()) - min(per.values())
    print(f"\n  {'GRUNT':<7s} {'cap (nF)':>10s} {'mech d(tilt)':>14s} {'defect':>9s} "
          f"{'sign ok':>8s}")
    n_ok = 0
    for nm in ("cut", "flat", "boost"):
        ok = (per[nm] < 0) == (need[nm] < 0)
        n_ok += int(ok)
        print(f"  {nm:<7s} {caps[nm] * 1e9:10.3f} {per[nm]:+14.6f} {need[nm]:+9.3f} "
              f"{str(ok):>8s}")
    print(f"\n  spread across GRUNT : {spread:.3e} dB/oct  (the mechanism is GRUNT-INDEPENDENT,")
    print(f"  as the linearity argument requires — this is the assertion, not the argument)")
    print(f"  sign agreement : {n_ok} of 3")
    if n_ok == 3:
        print(f"\n  ⭐ THE CANDIDATE PASSES THE SIGN GATE 3/3 — unlike the clipper's `a0` (AI, 1 of")
        print(f"     3) and the GRUNT caps' voltage coefficient (AJ4, 0 of 3).  It dies on SHAPE")
        print(f"     and SIZE instead.  ⇒ sign-admissibility is NECESSARY, NOT SUFFICIENT — a")
        print(f"     screen built on sign alone would have passed this carrier.")
    out["ak5"] = {"caps_nf": {k: v * 1e9 for k, v in caps.items()},
                  "per_grunt": per, "spread": spread, "n_sign_ok": n_ok}
    return n_ok, spread


# ---------------------------------------------------------------------------
# AK6 — the verdict
# ---------------------------------------------------------------------------
def gate_ak6(routes, n_sign_ok, out):
    print("\n" + "-" * 96)
    print("AK6  VERDICT — the J201 shaper, on all three routes")
    print("-" * 96)
    for r in routes:
        print(f"  {r['name']:<22s}: {r['verdict']}")
    n_reach = sum(0 if r["refuted"] else 1 for r in routes)
    print()
    if n_reach == 0:
        joint = ("ALL THREE ROUTES REFUTED — the J201's shaper is not item 6's carrier.  With "
                 "AJ's three pre-clipper carriers, AI's at-clipper `a0` and AF7's five "
                 "post-clipper carriers, the named-carrier search is now exhausted on both "
                 "sides of the clipper INCLUDING the J201's nonlinearity, and session 139's "
                 "NEXT #1(b) is closed.  The common root cause is structural: the degeneration "
                 "shelf's corners sit a decade below the vertex, so every route through it is "
                 "spent before it reaches the feature.")
        print("  ⛔ " + joint)
    else:
        joint = (f"{n_reach} of 3 routes REACH — the J201's shaper is a live carrier for item 6 "
                 f"and should be built and rendered.")
        print("  ⭐ " + joint)
    print(f"\n  ⚠ SCOPE — refuted is the J201 as a TILT mechanism AT THE VERTEX.  This gate says")
    print(f"    nothing about the J201's EVEN-ORDER harmonic role (`reference-sources.md` §4,")
    print(f"    still live and still the largest hardware gap in the project), and nothing about")
    print(f"    the bridged-T half of AB6.  Nothing here claims the deficit is unreal: AG3/AG5")
    print(f"    measured it at 1.72x the requirement.")
    if n_sign_ok == 3 and n_reach == 0:
        print(f"\n  ⭐ AND THE METHODOLOGICAL RESULT: this carrier PASSES item 6's GRUNT-sign gate")
        print(f"     3/3 and is still refuted.  Sign-admissibility is necessary, not sufficient.")
    out["ak6"] = {"n_reach": n_reach, "joint": joint,
                  "per_route": {r["name"]: r["verdict"] for r in routes}}
    return joint


def main():
    ap = argparse.ArgumentParser(description="GATE AK — the J201 shaper as a tilt mechanism")
    ap.add_argument("--ag", default=AG_REPORT)
    ap.add_argument("--ah", default=AH_REPORT)
    ap.add_argument("--ai", default=AI_REPORT)
    ap.add_argument("--json", default=OUT_JSON)
    a = ap.parse_args()

    for p in (a.ag, a.ah, a.ai):
        if not os.path.exists(p):
            _die(f"{p} not found — this gate reads its operands from stored reports and will not "
                 f"reconstruct them.")
    ag = json.load(open(a.ag))
    ah = json.load(open(a.ah))
    ai = json.load(open(a.ai))
    f0 = ag["vertex_hz"]
    half = ag["ag3"]["half_oct"]
    budget = ah["ah7"]["tilt_max_db_oct"]
    avail = ah["ah7"]["tilt_available"]
    need = ai["ai3"]["need"]
    if set(need) != {"cut", "flat", "boost"}:
        _die(f"AK — the stored GATE AI report's defect covers {sorted(need)}, not all three GRUNT "
             f"positions; the sign screen this gate reports is not evaluable.")

    gm, ro, rq2 = _consts()

    print("=" * 96)
    print("GATE AK — the J201's own SHAPER as a TILT mechanism for item 6's treble half")
    print("=" * 96)
    print(f"  vertex, window, budget and the DEFECT are READ from stored reports, never "
          f"transcribed:")
    print(f"      vertex {f0:.1f} Hz,  window +-{half} oct        [{os.path.basename(a.ag)}]")
    print(f"      AH7 budget {budget:+.3f} dB/oct, AG5 available {avail:+.3f} dB/oct"
          f"   [{os.path.basename(a.ah)}]")
    print(f"      defect per GRUNT: " + ", ".join(f"{k} {need[k]:+.3f}"
                                                  for k in ("cut", "flat", "boost"))
          + f"   [{os.path.basename(a.ai)}]")
    print(f"  shipped stage, read from FitParams.h: jfetGm {gm * 1e3:.4f} mS "
          f"(NOMINAL J201 is 0.69 mS), jfetRo {ro / 1e3:.1f}k, jfetRq2 {rq2 / 1e6:.2f}M")
    print(f"  ⚠ PREMISE, printed every run: GATE AJ refuted the J201's gate CAPACITANCE.  A")
    print(f"    capacitance and a transconductance are DIFFERENT carriers, so nothing here is")
    print(f"    inherited from AJ2 — this gate screens the shaper on its own terms.")

    out = {"ag_report": a.ag, "ah_report": a.ah, "ai_report": a.ai, "vertex_hz": f0,
           "half_oct": half, "budget": budget, "available": avail, "defect": need,
           "jfet_gm": gm, "jfet_ro": ro, "jfet_rq2": rq2}

    zin = AJ.ladder_zin(AI.FINE)
    gate_ak1(f0, half, gm, ro, rq2, zin, out)
    r1 = gate_ak2(f0, half, gm, ro, rq2, zin, budget, out)
    r2 = gate_ak3(f0, half, gm, ro, rq2, zin, budget, avail, ag["ag4"], out)
    r3 = gate_ak4(f0, half, gm, budget, out)
    n_sign_ok, _ = gate_ak5(f0, half, gm, ro, rq2, zin, need, out)
    gate_ak6([r1, r2, r3], n_sign_ok, out)

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\n  -> {a.json}")
    print("\n" + "=" * 96)
    print("GATE AK: all guards passed.  AK2-AK6 are readable.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
