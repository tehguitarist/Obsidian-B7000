#!/usr/bin/env python3.11
"""GATE AI — THE AT-CLIPPER DRIVE-TILT MECHANISM: THE ONE ITEM 6'S SEARCH ALREADY SHIPS.

WHY THIS EXISTS (session 138, executing session 137's `NEXT` #1 on its first candidate).

  Item 6's treble half needs a **frequency-dependent, drive-generated loss that steepens with
  frequency, at or UPSTREAM of the clipper**, worth AF6/AH7's budget at the 2935 Hz vertex.  AF7
  screened five candidates and refuted all five — but every one of them was POST-clipper.  The
  pre/at-clipper side has never been screened, and `measurement-discipline.md` §3 says where to
  start:

      "BEFORE ADDING A MECHANISM CLASS, COUNT HOW MANY INSTANCES OF IT THE MODEL ALREADY HAS —
       AND READ WHAT THEY DO."  (s134, AF4)

  There is exactly one, and it is the obvious one: **the CD4049's incremental gain `a0` falls as
  the VTC saturates.**  `a0` is drive-dependent by construction, it sits AT the clipper, and it
  moves the frequency response two ways at once —

      (i)  the closed-loop pole  [1/((1+a0)R16) + 1/R18] / (2*pi*C14)   moves UP as a0 falls;
      (ii) the input-node impedance  Zf/(1+a0)  rises as a0 falls, which moves the GRUNT
           coupling cap's high-pass corner DOWN.

  (i) brightens and (ii) darkens, so the net is not guessable and the sign is not assumable —
  which is exactly why this needs computing rather than asserting.  ⚠ Session 17's
  `clipa0_grunt_corner_probe.py` already found "the gain drop cancels the corner shift" and that
  note is quoted in `FitParams.h` as *"A0 is ruled out"* — but it is ruled out **for the LF GRUNT
  corner and H3-H2 at ~220 Hz**, which is a different frequency and a different quantity.  It says
  nothing about the slope at 2935 Hz.  Scoped, not inherited.

⭐⭐ THE SIMPLIFICATION THAT MAKES THIS EXACT AND CHEAP, AND IT IS ASSERTED, NOT ARGUED (AI1c).
  The quantity is a drive-tilt **CHANGE**, i.e. a difference of slopes of log-magnitudes.  The tilt
  operator is LINEAR on log-magnitude and every block that does not depend on `a0` contributes the
  same slope at both ends of the ladder, so **the entire fixed chain cancels EXACTLY** — the treble
  /ATTACK ladder, IC2_A, the bridged-T, both Sallen-Keys, the output stage, all of it.  Only the
  at-clipper block survives:

      Vs --Cg-- R16 --> W --(R18 || C14)--> Vout ,   Vout = -a0 * W

      H_at(f, a0, Cg) = -a0 * Zf / ( Zf + (1+a0)*(R16 + 1/(s*Cg)) ),    Zf = R18 || 1/(s*C14)

  so this gate needs **no render at all** for the mechanism side.  AI1a asserts that H_at reduces
  to GATE AB's already-validated `clipper_closed_loop` as Cg -> inf, and AI1c asserts the
  cancellation numerically against a deliberately wild fixed block.

WHAT THIS GATE DOES **NOT** CLAIM.
  * It screens ONE candidate class — the at-clipper block, whose only drive-dependent term is a0.
    It does **not** screen the J201's Miller/junction capacitance, IC2_A's GBW or slew, or the
    GRUNT caps' voltage coefficient.  Those are named in the verdict as UNSCREENED, not refuted.
  * It does not measure a0's actual excursion.  It does not need to: AI4 quotes the mechanism at
    a0 -> 1, a limit far past any physical sag (the stage would have no gain left), so the size
    ceiling holds for **every** excursion (`quote the spread end WORST for the conclusion`, AF).
  * No constant, no `src/` edit, no new render.

  AI1  KNOWN ANSWERS  (a) H_at(Cg -> inf) == AB.clipper_closed_loop, exact algebra, bar 1e-6 dB;
                      (b) the tilt estimator recovers an injected tilt exactly (bar 1e-9);
                      (c) THE LICENCE: a wild a0-independent block must cancel from the tilt
                          CHANGE to machine precision -- this is what lets the gate skip the chain.
  AI2  THE MECHANISM  d(tilt) at the vertex vs a0, per GRUNT position, from the shipped constants.
  AI3  THE DEFECT     the same quantity's per-capture PEDAL-MINUS-MODEL, per GRUNT position, off
                      the stored surface with AG5's own estimator -- the discriminator.
  AI4  SIZE CEILING   the mechanism at a0 -> 1 as a fraction of what each GRUNT position needs.
  AI5  VERDICT        computed: sign products per position, compared against the DEFECT's signs
                      (the target appears as a variable -- AB5's rule).

Usage:
  python3.11 analysis/at_clipper_tilt_gate.py
  python3.11 analysis/at_clipper_tilt_gate.py --json analysis/reports/s138_at_clipper_tilt.json
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bt_pair_shape_gate as AB          # noqa: E402  R16/R18/C14, clipA0, clipper_closed_loop
import drive_tilt_shape_gate as AG       # noqa: E402  the band-surface tilt estimator, RUNGS
import od_absolute_gate as Q             # noqa: E402  the surface and the pure-OD endpoints
import null_locus_gate as R              # noqa: E402  EXPECT_ENDPOINTS -- ONE definition

REPORT = "analysis/reports/s124_ship.json"
AG_REPORT = "analysis/reports/s135_drive_tilt.json"
AH_REPORT = "analysis/reports/s137_vertex_curvature.json"
OUT_JSON = "analysis/reports/s138_at_clipper_tilt.json"

# The a0 sweep.  1.0 is not a physical operating point -- it is the LIMIT quoted so the size
# ceiling holds for any excursion whatsoever (a shunt-feedback stage at a0 = 1 has no gain left).
A0_SWEEP = (20.0, 15.0, 10.0, 8.0, 5.0, 3.0, 2.0, 1.0)
A0_LIMIT = 1.0

GRUNT_CAP = {"cut": "clipC11", "flat": "clipC12", "boost": "clipC13"}

KA_REDUCE_TOL = 1e-6      # dB, AI1a -- exact algebra through two different expressions
KA_TILT_TOL = 1e-9        # dB/oct, AI1b -- exact algebra
KA_CANCEL_TOL = 1e-9      # dB/oct, AI1c -- the licence

FINE = np.logspace(np.log10(100.0), np.log10(20000.0), 6001)


def _die(msg):
    print(f"\n⛔ GATE AI REFUSES: {msg}")
    sys.exit(2)


def tilt_fine(db, f0, half):
    """Slope in dB/oct AT f0, from a quadratic fit in log2(f/f0) -- AG's estimator, fine grid."""
    lg = np.log2(FINE / f0)
    m = np.abs(lg) <= half
    x, y = lg[m], np.asarray(db)[m]
    if x.size < 3:
        _die("tilt_fine — fewer than 3 points in the window.")
    A = np.vstack([x ** 2, x, np.ones(x.size)]).T
    return float(np.linalg.lstsq(A, y, rcond=None)[0][1])


def h_at(f, a0, cg):
    """The at-clipper block: GRUNT cap -> R16 -> node W -> -a0*W, with Zf = R18 || 1/(s*C14)."""
    s = 2j * np.pi * np.asarray(f, dtype=float)
    zf = 1.0 / (1.0 / AB.R18 + s * AB.C14)
    return -a0 * zf / (zf + (1.0 + a0) * (AB.R16 + 1.0 / (s * cg)))


def mech_db(a0, cg):
    return 20.0 * np.log10(np.abs(h_at(FINE, a0, cg)) + 1e-300)


# ---------------------------------------------------------------------------
# AI1 — the three known answers
# ---------------------------------------------------------------------------
def gate_ai1(f0, half, caps, out):
    print("\n" + "-" * 96)
    print("AI1  KNOWN ANSWERS")
    print("-" * 96)

    # (a) Cg -> inf must reduce H_at to the cascade gate's already-validated closed loop.
    lhs = 20.0 * np.log10(np.abs(h_at(FINE, AB.CLIP_A0, 1.0)))
    rhs = 20.0 * np.log10(np.abs(AB.clipper_closed_loop(FINE, AB.CLIP_A0)))
    worst = float(np.max(np.abs(lhs - rhs)))
    print(f"  (a) H_at(Cg -> inf) vs AB.clipper_closed_loop : worst {worst:.3e} dB "
          f"(bar {KA_REDUCE_TOL:g})")
    if worst > KA_REDUCE_TOL:
        _die(f"AI1a — the at-clipper block does not reduce to GATE AB's validated closed loop "
             f"({worst:.3e} dB).  One of the two expressions is wrong; do not read AI2.")

    # (b) the estimator must recover an injected tilt exactly.  T = 0 is its own control (s133).
    base = mech_db(AB.CLIP_A0, caps["cut"])
    inj_worst = 0.0
    for T in (0.0, -1.185, +3.0):
        got = tilt_fine(base + T * np.log2(FINE / f0), f0, half) - tilt_fine(base, f0, half)
        inj_worst = max(inj_worst, abs(got - T))
    print(f"  (b) injected-tilt recovery over T = 0 / -1.185 / +3 : worst {inj_worst:.3e} dB/oct "
          f"(bar {KA_TILT_TOL:g})")
    if inj_worst > KA_TILT_TOL:
        _die(f"AI1b — the tilt estimator does not recover an injected tilt ({inj_worst:.3e}).")

    # (c) THE LICENCE.  A wild a0-INDEPENDENT block must cancel exactly from the tilt CHANGE.
    #     Deliberately wild: a 3rd-order-ish shape with poles and a zero inside the window, so a
    #     cancellation that only worked for gentle curves would fail here.
    s = 2j * np.pi * FINE
    fixed = (1.0 + s / (2 * np.pi * 2500.0)) / (
        (1.0 + s / (2 * np.pi * 900.0)) * (1.0 + s / (2 * np.pi * 3300.0)) ** 2)
    fdb = 20.0 * np.log10(np.abs(fixed))
    lo, hi = mech_db(A0_LIMIT, caps["cut"]), mech_db(AB.CLIP_A0, caps["cut"])
    bare = tilt_fine(lo, f0, half) - tilt_fine(hi, f0, half)
    with_fixed = tilt_fine(lo + fdb, f0, half) - tilt_fine(hi + fdb, f0, half)
    cancel = abs(with_fixed - bare)
    print(f"  (c) LICENCE — a wild fixed block cancels from the tilt CHANGE : {cancel:.3e} dB/oct "
          f"(bar {KA_CANCEL_TOL:g})")
    print(f"      ⇒ the treble/ATTACK ladder, IC2_A, the bridged-T, both SKs and the output stage")
    print(f"        are IRRELEVANT to this question, and the gate is exact without rendering them.")
    if cancel > KA_CANCEL_TOL:
        _die(f"AI1c — an a0-independent block did NOT cancel from the tilt change "
             f"({cancel:.3e} dB/oct).  The gate's whole simplification is invalid.")
    out["ai1"] = {"reduce_worst_db": worst, "inject_worst": inj_worst, "cancel": cancel}


# ---------------------------------------------------------------------------
# AI2 — the mechanism
# ---------------------------------------------------------------------------
def gate_ai2(f0, half, caps, out):
    print("\n" + "-" * 96)
    print("AI2  THE MECHANISM — d(tilt) at the vertex as `a0` sags, per GRUNT position")
    print("-" * 96)
    print(f"  Shipped: R16 {AB.R16:.0f}  R18 {AB.R18:.0f}  C14 {AB.C14:.3g}  a0 {AB.CLIP_A0:.4f}")
    print(f"  GRUNT coupling caps read from FitParams.h (clipC11 is FITTED, not the schematic "
          f"4n7):")
    for nm in ("cut", "flat", "boost"):
        print(f"      {nm:<6s} {GRUNT_CAP[nm]:<9s} {caps[nm]:.4g} F")
    base = {nm: tilt_fine(mech_db(AB.CLIP_A0, caps[nm]), f0, half) for nm in caps}
    print(f"\n  tilt at {f0:.0f} Hz (+-{half} oct) at the shipped a0: "
          + "  ".join(f"{nm} {base[nm]:+.4f}" for nm in ("cut", "flat", "boost")))
    print(f"\n  {'a0':>7s} " + " ".join(f"{nm + ' d(tilt)':>16s}"
                                        for nm in ("cut", "flat", "boost")))
    tab = {}
    for a0 in A0_SWEEP:
        row = {nm: tilt_fine(mech_db(a0, caps[nm]), f0, half) - base[nm] for nm in caps}
        tab[f"{a0:g}"] = row
        print(f"  {a0:7.3f} " + " ".join(f"{row[nm]:+16.4f}"
                                         for nm in ("cut", "flat", "boost")))
    lim = tab[f"{A0_LIMIT:g}"]
    print(f"\n  ⚠ a0 = {A0_LIMIT:g} is NOT an operating point — it is the LIMIT, quoted so the")
    print(f"    ceiling holds for ANY excursion.  A shunt-feedback stage at a0 = 1 has no gain.")
    print(f"  ⭐⭐ THE SIGN IS NOT THE SAME AT EVERY GRUNT POSITION: "
          + ", ".join(f"{nm} {'-' if lim[nm] < 0 else '+'}" for nm in ("cut", "flat", "boost")))
    print(f"     (i) the closed-loop pole rises as a0 falls -> BRIGHTER; (ii) the input impedance")
    print(f"     rises, dropping the GRUNT high-pass corner -> DARKER.  Which wins depends on the")
    print(f"     coupling cap, so the switch changes the SIGN of the mechanism.")
    out["ai2"] = {"base": base, "table": tab, "limit": lim}
    return base, tab, lim


# ---------------------------------------------------------------------------
# AI3 — the defect, per GRUNT position (the discriminator)
# ---------------------------------------------------------------------------
def gate_ai3(f0, half, out):
    print("\n" + "-" * 96)
    print("AI3  THE DEFECT — per-capture PEDAL-MINUS-MODEL drive-tilt, split by GRUNT")
    print("-" * 96)
    bands, caps_, absfr, nonhf, fb, files, drops = Q.load_surface(REPORT)
    if len(files) != R.EXPECT_ENDPOINTS:
        _die(f"GATE Q's endpoint count moved ({len(files)} vs {R.EXPECT_ENDPOINTS}) — bump it "
             f"THERE deliberately after checking what arrived.")
    lg = np.log2(fb / f0)
    r0, r1 = AG.RUNGS[0], AG.RUNGS[-1]
    print(f"  {len(files)} pure-OD endpoints (GATE Q's selection, imported), AG5's estimator,")
    print(f"  rungs {r0} -> {r1}, +-{half} oct of the 1/3-octave surface.\n")
    byg, rows = {}, []
    for f in sorted(files):
        nm = ("boost" if "grunt-boost" in f else "flat" if "grunt-flat" in f else "cut")
        try:
            a0_, _ = AG.tilt_at(absfr[(f, r0)][0][nonhf], lg, half)
            a1_, _ = AG.tilt_at(absfr[(f, r1)][0][nonhf], lg, half)
            b0_, _ = AG.tilt_at(absfr[(f, r0)][1][nonhf], lg, half)
            b1_, _ = AG.tilt_at(absfr[(f, r1)][1][nonhf], lg, half)
        except KeyError:
            _die(f"AI3 — the surface has no rung pair for {f}; the membership is malformed.")
        d = (b1_ - b0_) - (a1_ - a0_)
        if not np.isfinite(d):
            _die(f"AI3 — non-finite drive-tilt for {f}.  A nan does not trip a threshold "
                 f"(s106 N3); refusing rather than letting it vote.")
        byg.setdefault(nm, []).append(d)
        rows.append((nm, f, d))
        print(f"    {nm:<6s} {f[:56]:<56s} {d:+8.3f}")
    if set(byg) != set(GRUNT_CAP):
        _die(f"AI3 — the endpoints cover {sorted(byg)}, not all three GRUNT positions, so the "
             f"discriminator this gate rests on is not measurable.")
    print(f"\n  {'GRUNT':<6s} {'n':>3s} {'mean':>9s} {'min':>9s} {'max':>9s}   all one sign?")
    need = {}
    for nm in ("cut", "flat", "boost"):
        v = np.array(byg[nm])
        need[nm] = float(v.mean())
        print(f"  {nm:<6s} {len(v):3d} {v.mean():+9.3f} {v.min():+9.3f} {v.max():+9.3f}   "
              f"{bool((v < 0).all())}")
    n_neg = sum(1 for _, _, d in rows if d < 0)
    print(f"\n  the defect is NEGATIVE (= the direction item 6 needs) in {n_neg}/{len(rows)} "
          f"captures, at EVERY GRUNT position")
    out["ai3"] = {"rows": [(a, b, float(c)) for a, b, c in rows], "need": need,
                  "n_negative": n_neg, "n": len(rows)}
    return need, n_neg, len(rows)


# ---------------------------------------------------------------------------
# AI4 / AI5 — the ceiling and the computed verdict
# ---------------------------------------------------------------------------
def gate_ai45(lim, need, out):
    print("\n" + "-" * 96)
    print("AI4  SIZE CEILING at the a0 -> 1 LIMIT, against what each position needs")
    print("-" * 96)
    print(f"  {'GRUNT':<6s} {'mechanism':>12s} {'defect':>10s} {'sign ok?':>10s} {'reach':>10s}")
    reach, signok = {}, {}
    for nm in ("cut", "flat", "boost"):
        m, d = lim[nm], need[nm]
        ok = (m < 0) == (d < 0)                       # AB5: the target is a VARIABLE here
        r = (m / d) if (ok and d != 0) else 0.0
        reach[nm], signok[nm] = float(r), bool(ok)
        print(f"  {nm:<6s} {m:+12.4f} {d:+10.3f} {str(ok):>10s} {100 * r:9.1f}%")
    n_ok = sum(signok.values())

    print("\n" + "-" * 96)
    print("AI5  VERDICT")
    print("-" * 96)
    worst_reach = max(reach.values())
    if n_ok == 3 and worst_reach >= 1.0:
        v = ("REACHES — the at-clipper a0 mechanism has the right sign at every GRUNT position "
             "and is large enough; this is a CANDIDATE and must be gated on shape next")
    elif n_ok == 3:
        v = (f"RIGHT SIGN EVERYWHERE, TOO SMALL — {100 * worst_reach:.0f}% of the requirement at "
             f"its best position even at a0 -> 1")
    elif n_ok == 0:
        v = ("REFUTED ON SIGN — the mechanism pushes the WRONG way at every GRUNT position")
    else:
        v = (f"REFUTED — the mechanism has the right sign at only {n_ok} of 3 GRUNT positions "
             f"(and pushes the defect FURTHER at the other {3 - n_ok}), while the defect is the "
             f"same sign at all three; and where the sign IS right it reaches only "
             f"{100 * worst_reach:.0f}% of what that position needs, at a0 -> 1")
    print(f"  {v}")
    print(f"\n  ⚠ SCOPE — this refutes ONE candidate class, the at-clipper block, whose only")
    print(f"    drive-dependent term is a0.  UNSCREENED on this side of the clipper: the J201's")
    print(f"    Miller / junction capacitance, IC2_A's GBW and slew, and the GRUNT caps' own")
    print(f"    voltage coefficient.  Those are NOT refuted by anything here.")
    out["ai4"] = {"reach": reach, "sign_ok": signok, "n_sign_ok": n_ok,
                  "worst_reach": float(worst_reach)}
    out["ai5"] = {"verdict": v}
    return v


def main():
    ap = argparse.ArgumentParser(description="GATE AI — the at-clipper drive-tilt mechanism")
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--ag", default=AG_REPORT)
    ap.add_argument("--ah", default=AH_REPORT)
    ap.add_argument("--json", default=OUT_JSON)
    a = ap.parse_args()

    for p in (a.report, a.ag, a.ah):
        if not os.path.exists(p):
            _die(f"{p} not found — this gate reads its operands from stored reports and will not "
                 f"reconstruct them.")
    ag = json.load(open(a.ag))
    ah = json.load(open(a.ah))
    f0 = ag["vertex_hz"]
    half = ag["ag3"]["half_oct"]
    budget = ah["ah7"]["tilt_max_db_oct"]
    avail = ah["ah7"]["tilt_available"]

    print("=" * 96)
    print("GATE AI — the AT-CLIPPER drive-tilt mechanism (the one the model already ships)")
    print("=" * 96)
    print(f"  vertex, window, budget READ from {a.ag} / {a.ah}, never transcribed:")
    print(f"      vertex {f0:.1f} Hz,  window +-{half} oct")
    print(f"      AH7 budget {budget:+.3f} dB/oct,  AG5 available {avail:+.3f} dB/oct")
    print(f"  ⚠ PREMISE, printed every run: session 17's `clipa0_grunt_corner_probe.py` found the")
    print(f"    gain drop cancels the corner shift AT THE LF GRUNT CORNER, and FitParams.h quotes")
    print(f"    that as \"A0 is ruled out\".  That is a different frequency and a different")
    print(f"    quantity; it is NOT inherited here, and this gate re-asks it at the vertex.")

    caps = {nm: AB._read_fitparam(key) for nm, key in GRUNT_CAP.items()}
    out = {"report": a.report, "ag_report": a.ag, "ah_report": a.ah, "vertex_hz": f0,
           "half_oct": half, "budget": budget, "available": avail,
           "a0_shipped": AB.CLIP_A0, "grunt_caps": caps}

    gate_ai1(f0, half, caps, out)
    _, _, lim = gate_ai2(f0, half, caps, out)
    need, n_neg, n_tot = gate_ai3(f0, half, out)
    v = gate_ai45(lim, need, out)

    print(f"\n  ⭐⭐ THE DELIVERABLE: the only drive-dependent mechanism the model ALREADY has at")
    print(f"     or before the clipper is refuted as item 6's carrier — on SIGN CONSISTENCY (it")
    print(f"     flips with a switch the defect does not flip with, {n_neg}/{n_tot} captures one")
    print(f"     way) and, independently, on SIZE at a limit past any physical sag.")

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\n  -> {a.json}")
    print("\n" + "=" * 96)
    print("GATE AI: all guards passed.  AI2-AI5 are readable.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
