#!/usr/bin/env python3.11
"""GATE AJ — THE THREE UNSCREENED **PRE-CLIPPER** CANDIDATES FOR ITEM 6'S TREBLE HALF.

WHY THIS EXISTS (session 139, executing session 138's `NEXT` #1 to completion).

  Item 6's treble half needs a **frequency-dependent, drive-generated loss that steepens with
  frequency, at or UPSTREAM of the clipper**, worth AH7's budget at the 2935 Hz vertex.  The
  screen so far:

      AF7 (s134)  five POST-clipper carriers          -> 0 of 5 reach
      AI  (s138)  the at-clipper `a0` sag             -> REFUTED on sign consistency AND size

  AI's own printed scope named exactly what was left, and this gate takes all three:

      AJ2  the J201's Miller / voltage-dependent junction capacitance
      AJ3  IC2_A's GBW and slew  (AF2/AF3's arguments re-run PRE-clipper, where the swing is
           larger -- which is the whole reason session 138 asked for them again)
      AJ4  the GRUNT caps' own voltage coefficient

⭐⭐ THE LICENCE, INHERITED FROM AI1c AND RE-ASSERTED HERE ON THIS GATE'S OWN BLOCKS.
  The graded quantity is a drive-tilt **CHANGE** -- a difference of slopes of log-magnitudes.
  The tilt operator is LINEAR on log-magnitude, so every block that does not depend on the
  candidate's parameter contributes the same slope at both ends of the ladder and **cancels
  EXACTLY**.  ⇒ no render, for any of the three.  AJ1a asserts it numerically against a
  deliberately wild fixed block rather than arguing it from the algebra.

⭐⭐⭐ THE RESULT THAT GENERALISES BEYOND ALL THREE CANDIDATES (AJ2c).
  Every "a capacitance grows with drive" mechanism is **one real pole whose corner moves**.  For
  such a pole the tilt change is  dT(f) = -6.0206 * u/(1+u),  u = (f/fp)^2,  and

      d ln|dT| / d ln f  =  2 / (1 + u)   <=  2 ,   EXACTLY, for every fp and every f.

  So the class cannot produce a deficit that steepens FASTER than the square of frequency.
  AG4 measured the deficit's own exponent over the only three uncontaminated centres, and it is
  **steeper than 2**.  That is a structural screen with no size argument in it and no threshold
  to argue about -- the size refutation below is the second, independent one.
  ⚠ n = 3 centres.  Reported as a bound the class must satisfy and a measurement that exceeds
  it, NOT as a fit.

  ⛔⛔ SESSION 141 CORRECTION -- THE CONCLUSION STANDS, THIS GATE'S PHRASING AND ITS GATING
  STATISTIC DO NOT.  Do NOT re-quote AJ2c as *"every adjacent pair exceeds the bound"*.
  GATE AL (`analysis/deficit_exponent_gate.py`) re-measured the exponent on GATE W's 1/48-oct
  transfer -- a 14x finer surface, 12 non-overlapping centres, 4x this gate's n -- and found:
    (1) the deficit does NOT beat the bound POINTWISE (weakest 1/3-oct pair -0.117, weakest raw
        adjacent pair -10.349), so the "every pair" wording is false off this gate's own grid;
    (2) the per-pair statistic is NOT SCALE-FREE -- it divides a log-ratio by the centre
        spacing, so narrowing the half-width divides the same noise by a smaller number (the raw
        adjacent minimum runs -10.3 at 1/24 oct -> +2.02 at 1/6 oct on ONE dataset whose
        regression barely moves).  AJ2c's version was sound ONLY because its three centres sit a
        fixed 1/3 octave apart; it does not generalise, and it is not the statistic to build on;
    (3) the statistic the pointwise bound EXACTLY implies is the ENDPOINT one -- integrating
        d ln|g|/d ln f <= 2 over [a, b] gives endpoint exponent <= 2 for the whole class,
        whatever it does in between.  No fit, largest lever arm, cannot be rescued by a
        favourable interior.  Measured over the rising limb: **> 2 at 5/5 half-widths, smallest
        2.530**, limb regression 2.53-2.90 (AG4's 2.841 reproduces as 2.685).
    (4) and |D| is NOT MONOTONE across the band -- interior minimum at ~1348 Hz -- so AG4's
        three centres (1613/2032/2560) all sit on ONE LIMB and a single power law over the whole
        band is not even defined.
  ⇒ the single-moving-pole class IS refuted as the carrier of the whole rising limb, and was
  NEVER refuted pointwise.  QUOTE AL4's ENDPOINT READING, not this gate's pair column.  The
  readings below are kept unchanged so every pre-s141 quote stays reproducible.

WHAT THIS GATE DOES **NOT** CLAIM.
  * It does not measure how far the J201's junction capacitance actually moves.  It does not
    need to: AJ2 SOLVES for the capacitance required and compares against a ceiling set well
    ABOVE the part's datasheet maximum, so the verdict holds for any excursion (`quote the
    spread end WORST for the conclusion`, AF).
  * AJ3's GBW half is **INHERITED, not re-derived** -- AF2 established that gain-bandwidth is a
    SMALL-SIGNAL parameter, so no amplitude moves it, and that argument is about the part, not
    about which stage it sits in.  What is new here is the SLEW number at IC2_A's own node.
  * No constant, no `src/` edit, no new render.

  AJ1  KNOWN ANSWERS  (a) THE LICENCE: a wild candidate-independent block cancels from the tilt
                          CHANGE (bar 1e-9 dB/oct);
                      (b) injected-tilt recovery, T = 0 its own control (bar 1e-9);
                      (c) the gate-node block reduces to JfetStage.h's documented oracle
                          `kDiv * HP(s)` as Cin -> 0 (bar 1e-6 dB);
                      (d) the treble ladder's input impedance, extracted two independent ways
                          from eq_reference's validated solve (bar 1e-9 relative).
  AJ2  CANDIDATE 1    J201 Miller / junction capacitance: the Miller factor from the SHIPPED gm,
                      the capacitance REQUIRED, the reach, and the exponent bound above.
  AJ3  CANDIDATE 2    IC2_A GBW (inherited structural refutation + a size row) and slew (new).
  AJ4  CANDIDATE 3    GRUNT-cap voltage coefficient, on AI's own at-clipper block, with the
                      GRUNT-consistency screen AI added as item 6's fourth gate.
  AJ5  VERDICT        computed per candidate against all four of item 6's pre-registered gates,
                      with the target appearing as a VARIABLE (AB5's rule).

Usage:
  python3.11 analysis/pre_clipper_tilt_gate.py
  python3.11 analysis/pre_clipper_tilt_gate.py --json analysis/reports/s139_pre_clipper_tilt.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import at_clipper_tilt_gate as AI       # noqa: E402  h_at, tilt_fine, FINE, grunt_caps
import bt_pair_shape_gate as AB         # noqa: E402  R16/R18/C14, CLIP_A0, _read_fitparam
import sk_mechanism_locus as AF         # noqa: E402  TL07x specs + rails, read from FitParams

# eq_reference prints a large reference dump at MODULE level (it has no __main__ guard), which
# would bury this gate's own output.  Suppressed on import only -- the module's functions are
# what we want, and silencing them would be a different thing entirely.
import contextlib                       # noqa: E402
import io                               # noqa: E402
with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ           # noqa: E402  treble_attack_tf, jfet_source_z
    import resonance_census as AM       # noqa: E402  shipped_treble / drawn_treble (s149)

# ⚠⚠ WHICH TREBLE-LADDER ELEMENT SET `ladder_zin` USES.  'shipped' is correct and is the default;
# 'drawn' reproduces every pre-session-149 number in this gate, GATE AK and GATE AN.  Settable from
# the environment so GATE AO can run a whole gate BOTH ways in isolated subprocesses and diff the
# stored reports -- a module-level flag mutated in-process is the s133 thread-race trap, and a
# subprocess has no shared state to leak.
LADDER_VALS = os.environ.get("B7K_LADDER_VALS", "shipped")

AG_REPORT = "analysis/reports/s135_drive_tilt.json"
AH_REPORT = "analysis/reports/s137_vertex_curvature.json"
AI_REPORT = "analysis/reports/s138_at_clipper_tilt.json"
OUT_JSON = "analysis/reports/s139_pre_clipper_tilt.json"

# --- J201 stage, schematic-verified input network (JfetStage.h kR4/kR5/kC2) ----------------
J_R4, J_R5, J_C2 = 100.0e3, 1.0e6, 1.0e-9
J_R6, J_C3 = 3.3e3, 220.0e-9

# --- IC2_A DRIVE stage, schematic-verified (circuit.md "DRIVE gain stage") -----------------
D_R15, D_C10, D_R17, D_R32 = 330.0e3, 47.0e-12, 3.3e3, 1.0e3
D_RDRIVE_MAXGAIN = 0.0        # DRIVE at minimum resistance == MAXIMUM closed-loop gain

# --- J201 gate capacitance ceilings.  Both quoted WORST for the conclusion. -----------------
# Vishay/onsemi J201 small-signal data: Ciss ~ 4 pF max, Crss ~ 1.5 pF max.  CEILING is set
# 2.5x above the datasheet maximum so the verdict survives any part-spread argument, and the
# gate additionally SOLVES for the value required rather than resting on either number.
J201_CISS_MAX_PF = 4.0
J201_CRSS_MAX_PF = 1.5
J201_CIN_CEILING_PF = 10.0

# --- Film vs ceramic voltage coefficient, |dC/C| over the working swing ---------------------
# Film (polyester/polypropylene) is essentially inert; X7R ceramic is not.  The gate reports
# the REQUIRED fraction against both, so it does not rest on knowing which part is fitted.
VCO_FILM = 0.001      # 0.1 %
VCO_X7R = 0.50        # 50 %  -- the pessimistic ceramic case, deliberately generous

KA_TOL_DB = 1e-6
KA_TOL_TILT = 1e-9
KA_TOL_REL = 1e-9

SINGLE_POLE_EXPONENT_BOUND = 2.0     # d ln|dT| / d ln f = 2/(1+u), exact


def _die(msg):
    print(f"\n⛔ GATE AJ REFUSES: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# Blocks
# ---------------------------------------------------------------------------
def ladder_kwargs(position="flat", which=None):
    """The element set the ladder Zin is computed FROM.  'shipped' | 'drawn' | a dict.

    ⚠⚠ CORRECTED SESSION 149 — this function did not exist, and `ladder_zin` below called
    `EQ.treble_attack_tf(f, position)` with eq_reference's **DRAWN** defaults.  Sessions 99/100
    re-fitted SEVENTEEN treble/ATTACK constants and changed the topology (R8/R11 became a tap
    ladder, the C5 leg gained a damping resistor, `trebleC8` ships at **0** — C8 out of circuit),
    so the drawn set is not the network the plugin runs: R7 x8.23, C6 x0.063, C7 x0.0076.  GATE AM
    hit exactly this and guards it (AM1a's shipped-vs-drawn divergence guard); GATE AJ, and through
    `ladder_zin` also GATE AK and GATE AN, did not.  `verify-the-BASELINE-not-its-LABEL`.

    Imported from `resonance_census`, never transcribed — one definition of "the shipped ladder"
    for the whole analysis tree (s145 AM5: import the source gate's FUNCTIONS, not its summary).
    'drawn' is kept reachable so every pre-s149 number stays reproducible, and GATE AO diffs the
    two rather than asserting the difference is small.
    """
    which = LADDER_VALS if which is None else which
    if isinstance(which, dict):
        return dict(which)
    if which == "shipped":
        return AM.shipped_treble(position)
    if which == "drawn":
        return AM.drawn_treble()
    _die(f"ladder_kwargs — unknown element set {which!r}; expected 'shipped', 'drawn' or a dict.")


def ladder_divergence(position="flat"):
    """(n_moved, total, {name: (drawn, shipped)}) — AM1a's guard, re-asserted where AJ uses it.

    A gate that computes Zin from the wrong value set still runs and still prints plausible,
    monotone numbers; the only thing that catches it is asserting the two sets actually DIFFER.
    """
    dr, sh = AM.drawn_treble(), AM.shipped_treble(position)
    moved = {k: (dr[k], sh[k]) for k in dr if not math.isclose(dr[k], sh[k], rel_tol=1e-9)}
    return len(moved), len(dr), moved


def ladder_zin(f, position="flat", zs_probe=1.0e3, which=None):
    """Input impedance of the treble/ATTACK ladder at node G (the J201 drain).

    Extracted from eq_reference's ALREADY-VALIDATED nodal solve rather than re-deriving the
    network: with a Thevenin source of impedance Zs the ladder sees a divider, so

        tf(Zs) / tf(0) = Zin / (Zin + Zs)   =>   Zin = Zs * ratio / (1 - ratio)

    AJ1d asserts that two different probe impedances return the same Zin.

    ⚠⚠ `which` selects the ELEMENT SET — see `ladder_kwargs`.  It defaults to the module-level
    `LADDER_VALS`, i.e. the SHIPPED ladder, corrected session 149.
    """
    kw = ladder_kwargs(position, which)
    h0 = EQ.treble_attack_tf(f, position, **kw)
    hz = EQ.treble_attack_tf(f, position, Zs=zs_probe, **kw)
    ratio = np.asarray(hz) / np.asarray(h0)
    return zs_probe * ratio / (1.0 - ratio)


def jfet_gate_block_db(f, cin, r4=J_R4, r5=J_R5, c2=J_C2):
    """Vg/Vin for  Vin --C2-- X --R4-- G --R5|Cin-- GND.

    At cin = 0 this is exactly JfetStage.h's documented oracle  kDiv * HP(s)  (AJ1c).
    """
    s = 2j * np.pi * np.asarray(f, dtype=float)
    yg = 1.0 / r5 + s * cin
    zg = 1.0 / yg
    h = zg / (1.0 / (s * c2) + r4 + zg)
    return 20.0 * np.log10(np.abs(h))


def miller_cin(f, cgd_f, cgs_f, gm):
    """Cin(f) = Cgs + Cgd*(1 + |A(f)|),  A = gm * |Z_drain|,  Z_drain = Zout_jfet || Zin_ladder."""
    zout = EQ.jfet_source_z(f, gm=gm, ro=AB._read_fitparam("jfetRo"),
                            Rq2=AB._read_fitparam("jfetRq2"), R6=J_R6, C3=J_C3)
    zin = ladder_zin(f)
    zd = 1.0 / (1.0 / zout + 1.0 / zin)
    a = gm * np.abs(zd)
    return cgs_f + cgd_f * (1.0 + a), a, np.abs(zd)


def tilt_change_from_cin(cin, f0, half):
    """d(tilt) at the vertex when the gate node acquires Cin, relative to Cin = 0."""
    return (AI.tilt_fine(jfet_gate_block_db(AI.FINE, cin), f0, half)
            - AI.tilt_fine(jfet_gate_block_db(AI.FINE, 0.0), f0, half))


def solve_required(fn, target, lo, hi):
    """Smallest x in [lo, hi] with fn(x) == target, by bisection on log x.

    Returns None when no root exists IN DIRECTION -- which is a COMPUTED VERDICT (reach 0), not
    a refusal: `no setting of X reaches the target in DIRECTION` is a STRONGER refutation than
    any size argument, and s134's GATE AF threw exactly that away by exiting.
    """
    flo, fhi = fn(lo) - target, fn(hi) - target
    if flo * fhi > 0.0:
        return None
    a, b = math.log(lo), math.log(hi)
    for _ in range(60):        # log-space bisection: 60 halvings is already past double precision
        m = 0.5 * (a + b)
        if (fn(math.exp(m)) - target) * flo > 0.0:
            a = m
        else:
            b = m
    return math.exp(0.5 * (a + b))


# ---------------------------------------------------------------------------
# AJ1 — known answers
# ---------------------------------------------------------------------------
def gate_aj1(f0, half, out):
    print("\n" + "-" * 96)
    print("AJ1  KNOWN ANSWERS")
    print("-" * 96)

    # (a) THE LICENCE, re-asserted on THIS gate's blocks.
    s = 2j * np.pi * AI.FINE
    fixed = (1.0 + s / (2 * np.pi * 2500.0)) / (
        (1.0 + s / (2 * np.pi * 900.0)) * (1.0 + s / (2 * np.pi * 3300.0)) ** 2)
    fdb = 20.0 * np.log10(np.abs(fixed))
    lo_db = jfet_gate_block_db(AI.FINE, 300.0e-12)
    hi_db = jfet_gate_block_db(AI.FINE, 0.0)
    bare = AI.tilt_fine(lo_db, f0, half) - AI.tilt_fine(hi_db, f0, half)
    withf = AI.tilt_fine(lo_db + fdb, f0, half) - AI.tilt_fine(hi_db + fdb, f0, half)
    cancel = abs(withf - bare)
    print(f"  (a) LICENCE — a wild candidate-independent block cancels from the tilt CHANGE : "
          f"{cancel:.3e} dB/oct (bar {KA_TOL_TILT:g})")
    if cancel > KA_TOL_TILT:
        _die(f"AJ1a — a candidate-independent block did NOT cancel ({cancel:.3e} dB/oct).  The "
             f"whole no-render simplification is invalid; do not read AJ2-AJ4.")

    # (b) injected-tilt recovery.  T = 0 is its own control (s133).
    inj = 0.0
    for T in (0.0, -1.199, +3.0):
        got = (AI.tilt_fine(hi_db + T * np.log2(AI.FINE / f0), f0, half)
               - AI.tilt_fine(hi_db, f0, half))
        inj = max(inj, abs(got - T))
    print(f"  (b) injected-tilt recovery over T = 0 / -1.199 / +3 : worst {inj:.3e} dB/oct "
          f"(bar {KA_TOL_TILT:g})")
    if inj > KA_TOL_TILT:
        _die(f"AJ1b — the tilt estimator does not recover an injected tilt ({inj:.3e}).")

    # (c) the gate block must reduce to JfetStage.h's own documented oracle at Cin = 0.
    hp = (1j * 2 * np.pi * AI.FINE * (J_R4 + J_R5) * J_C2
          / (1.0 + 1j * 2 * np.pi * AI.FINE * (J_R4 + J_R5) * J_C2))
    oracle = 20.0 * np.log10(np.abs(hp * (J_R5 / (J_R4 + J_R5))))
    worst = float(np.max(np.abs(hi_db - oracle)))
    print(f"  (c) gate block at Cin -> 0 vs JfetStage.h's `kDiv * HP(s)` oracle : worst "
          f"{worst:.3e} dB (bar {KA_TOL_DB:g})")
    if worst > KA_TOL_DB:
        _die(f"AJ1c — the gate-node block does not reduce to the shipped stage's own documented "
             f"input transfer ({worst:.3e} dB).  One of the two is wrong.")

    # (d) the ladder input impedance, two independent probe impedances.
    z1 = ladder_zin(AI.FINE, zs_probe=1.0e3)
    z2 = ladder_zin(AI.FINE, zs_probe=47.0e3)
    rel = float(np.max(np.abs(z1 - z2) / np.abs(z1)))
    print(f"  (d) ladder Zin from two probe impedances (1k, 47k) : worst rel {rel:.3e} "
          f"(bar {KA_TOL_REL:g})")
    if rel > KA_TOL_REL:
        _die(f"AJ1d — the ladder input impedance is probe-dependent ({rel:.3e}), so the Miller "
             f"factor built on it is not a measurement.")

    # (e) ⚠⚠ ADDED SESSION 149 — the EPOCH guard, and its absence was a real defect.  Until s149
    # this gate computed `ladder_zin` from eq_reference's DRAWN defaults while s99/s100's fit had
    # moved 11 of 12 treble values (R7 x8.23, C6 x0.063, C7 x0.0076, C8 -> 0), and GATE AK and
    # GATE AN inherited the same Zin through this function.  Nothing caught it because a
    # probe-independence check (d) is satisfied by ANY network -- it validates the extraction, not
    # the value set (`for any known answer of the form "my implementation agrees with a trusted
    # one", the shared INPUT is what the check cannot validate`, s145 AM1a).  GATE AM already had
    # this guard; the correction is only complete once the gate that USES the value carries it too.
    n_div, n_tot, _ = ladder_divergence("flat")
    print(f"  (e) shipped-vs-drawn ladder divergence : {n_div}/{n_tot} values differ  "
          f"(element set '{LADDER_VALS}', bar >= 10)")
    if LADDER_VALS == "shipped" and n_div < 10:
        _die(f"AJ1e — only {n_div} of {n_tot} treble values differ between the shipped and drawn "
             f"sets, but s99/s100 re-fitted 17 of them. Either `shipped_treble` has started "
             f"returning the drawn set, or the fit was reverted; either way this gate would be "
             f"screening a network the plugin does not run. GATE AO's whole subject.")
    out["aj1"] = {"cancel": cancel, "inject_worst": inj, "oracle_worst_db": worst,
                  "zin_rel": rel, "ladder_vals": LADDER_VALS, "ladder_divergent": n_div}


# ---------------------------------------------------------------------------
# AJ2 — candidate 1: the J201's Miller / junction capacitance
# ---------------------------------------------------------------------------
def gate_aj2(f0, half, budget, avail, ag4, out):
    print("\n" + "-" * 96)
    print("AJ2  CANDIDATE 1 — the J201's Miller / voltage-dependent junction capacitance")
    print("-" * 96)
    gm = AB._read_fitparam("jfetGm")
    cin_ds, a_vec, zd = miller_cin(AI.FINE, J201_CRSS_MAX_PF * 1e-12,
                                   (J201_CISS_MAX_PF - J201_CRSS_MAX_PF) * 1e-12, gm)
    i0 = int(np.argmin(np.abs(AI.FINE - f0)))
    a_at, zd_at, cin_at = float(a_vec[i0]), float(zd[i0]), float(cin_ds[i0])

    print(f"  shipped jfetGm {gm * 1e3:.4f} mS   (FitParams.h; the NOMINAL J201 is 0.69 mS)")
    print(f"  at the {f0:.0f} Hz vertex:  |Z_drain| = Zout_jfet || Zin_ladder = "
          f"{zd_at / 1e3:.3f} kohm")
    print(f"                              |A| = gm*|Z_drain| = {a_at:.4f}")
    # ⛔⛔ CORRECTED SESSION 149.  This block used to PRINT `|A| = {a_at:.2f} < 1` and conclude that
    # the candidate "reduces to the BARE junction capacitance" — a hardcoded comparison, i.e.
    # `computed-verdicts-not-narrated` in the one place it inverts a physical claim.  On the DRAWN
    # ladder |A| really was 0.565; on the SHIPPED ladder it is 2.778, so the old text printed
    # "2.78 < 1".  GATE AO carries the full correction; the size refutation below is unaffected
    # (it is read at an absolute ceiling), and AJ2c's exponent bound is analytic.
    if a_at < 1.0:
        print(f"\n  ⭐⭐ MILLER MULTIPLICATION NEEDS VOLTAGE GAIN, AND THIS STAGE HAS |A| = "
              f"{a_at:.3f} < 1")
        print(f"     at the vertex — it is a transconductance into a ~{zd_at / 1e3:.1f} kohm "
              f"ladder,")
        print(f"     not a voltage amplifier.  The Miller factor (1+|A|) is {1 + a_at:.3f}, so the")
        print(f"     'Miller' candidate reduces to the BARE junction capacitance.")
    else:
        print(f"\n  ⚠⚠ |A| = {a_at:.3f} >= 1 AT THE VERTEX, so there IS Miller multiplication and")
        print(f"     the candidate does NOT reduce to the bare junction capacitance.  The Miller")
        print(f"     factor (1+|A|) is {1 + a_at:.3f} — this row's refutation therefore rests on")
        print(f"     SIZE (the reach at the ceiling below) and on AJ2c's exponent bound, NOT on the")
        print(f"     absence of multiplication.  ⛔ Do not re-quote '|A| < 1' (GATE AO, s149).")
    print(f"\n  Cin at the datasheet MAXIMUM (Ciss {J201_CISS_MAX_PF:.1f} pF, Crss "
          f"{J201_CRSS_MAX_PF:.1f} pF) : {cin_at * 1e12:.2f} pF")

    # The capacitance REQUIRED, solved rather than asserted.
    lo, hi = 1e-13, 1e-6
    req = {}
    for nm, tgt in (("budget", budget), ("available", avail)):
        r = solve_required(lambda c: tilt_change_from_cin(c, f0, half), tgt, lo, hi)
        req[nm] = r
        if r is None:
            print(f"  Cin required to deliver the {nm} ({tgt:+.3f} dB/oct) : NO ROOT IN DIRECTION")
        else:
            print(f"  Cin required to deliver the {nm} ({tgt:+.3f} dB/oct) : {r * 1e12:.1f} pF")

    print(f"\n  {'Cin (pF)':>10s} {'d(tilt) @ vertex':>18s}   note")
    rows = []
    for c_pf in (cin_at * 1e12, J201_CIN_CEILING_PF, 30.0, 100.0, 300.0, 1000.0):
        d = tilt_change_from_cin(c_pf * 1e-12, f0, half)
        rows.append({"cin_pf": float(c_pf), "dtilt": float(d)})
        note = ""
        if abs(c_pf - cin_at * 1e12) < 1e-9:
            note = "<- the part, at its datasheet MAX"
        elif abs(c_pf - J201_CIN_CEILING_PF) < 1e-9:
            note = f"<- CEILING, {J201_CIN_CEILING_PF / J201_CISS_MAX_PF:.1f}x the datasheet max"
        print(f"  {c_pf:10.2f} {d:18.5f}   {note}")

    d_ceiling = tilt_change_from_cin(J201_CIN_CEILING_PF * 1e-12, f0, half)
    reach = abs(d_ceiling / budget) if budget else 0.0
    sign_ok = (d_ceiling < 0) == (budget < 0)
    print(f"\n  REACH at the ceiling, against AH7's budget {budget:+.3f} dB/oct : "
          f"{100 * reach:.3f} %   (sign ok: {sign_ok})")
    if req["budget"] is not None:
        print(f"  ⇒ the required {req['budget'] * 1e12:.0f} pF is {req['budget'] / cin_at:.0f}x "
              f"the WHOLE input capacitance the part has at its datasheet maximum,")
        print(f"     and it would have to be delivered by the DRIVE-DEPENDENT PART of it alone.")

    # Bound the Miller approximation itself rather than assuming it.  Splitting Cgd gives an
    # output-side pole at 1/(2*pi*|Z_drain|*Cgd) and a feedforward zero at gm/(2*pi*Cgd); if
    # either landed near the vertex the single-input-pole treatment would be wrong.
    f_out = 1.0 / (2 * np.pi * zd_at * J201_CRSS_MAX_PF * 1e-12)
    f_zero = gm / (2 * np.pi * J201_CRSS_MAX_PF * 1e-12)
    print(f"\n  Miller-split sanity — the two terms this treatment DROPS, so the approximation is")
    print(f"  bounded rather than assumed:  drain-side pole {f_out / 1e6:.1f} MHz "
          f"({f_out / f0:.0f}x the vertex),")
    print(f"  feedforward zero {f_zero / 1e6:.1f} MHz ({f_zero / f0:.0f}x).  Both are decades "
          f"clear; the input pole is the whole story.")

    # ---- AJ2c: the exponent bound that generalises past this candidate --------------------
    print("\n  " + "." * 92)
    print("  AJ2c  THE STRUCTURAL SCREEN — a moving single pole cannot steepen faster than f^2")
    print("  " + "." * 92)
    rows4 = [r for r in ag4["rows"] if r[3]]
    if len(rows4) < 3:
        _die(f"AJ2c — AG4 reports {len(rows4)} uncontaminated centres, fewer than the 3 its own "
             f"finding rests on; the exponent cannot be estimated and this gate will not "
             f"substitute contaminated ones.")
    fs = np.array([r[0] for r in rows4])
    dfc = np.array([r[2] - r[1] for r in rows4])          # PEDAL - MODEL, AG4's own columns
    if np.any(dfc >= 0.0):
        _die("AJ2c — a counted AG4 centre has a non-negative deficit, so log|D| is not the right "
             "statistic there; refusing rather than taking a log of a sign change.")
    expo = float(np.polyfit(np.log(fs), np.log(np.abs(dfc)), 1)[0])
    # With n = 3 a single regression slope is one number over three points; the ADJACENT-PAIR
    # exponents are the cheap robustness column that says whether the fit is describing the
    # whole span or being carried by one end (`check-n-before-reading-a-trend`, s82).
    pair = [float(np.log(abs(dfc[i + 1]) / abs(dfc[i])) / np.log(fs[i + 1] / fs[i]))
            for i in range(len(fs) - 1)]
    print(f"  AG4's uncontaminated centres (Hz)      : "
          + "  ".join(f"{f:.1f}" for f in fs))
    print(f"  deficit  PEDAL-MODEL  (dB/oct)         : "
          + "  ".join(f"{d:+.3f}" for d in dfc))
    print(f"\n  measured exponent  d ln|D| / d ln f   : {expo:.3f}")
    print(f"  adjacent-pair exponents (robustness)   : "
          + "  ".join(f"{p:.3f}" for p in pair)
          + f"   -> min {min(pair):.3f}")
    print(f"  the class's EXACT bound  2/(1+u)      : <= {SINGLE_POLE_EXPONENT_BOUND:.3f}, for "
          f"every pole frequency and every f")
    # Gate on the WEAKEST adjacent pair, not on the regression slope: that is the reading most
    # favourable to the candidate, so clearing it is the stricter statement.
    # ⛔ s141: this statistic is NOT scale-free and does NOT generalise off these three
    # fixed-1/3-oct centres — see the AJ2c correction block in the module docstring.  It is left
    # computing exactly what it always did (pre-s141 quotes stay reproducible); what changed is
    # what may be QUOTED from it, and the printed verdict below now says so.
    shape_ok = min(pair) <= SINGLE_POLE_EXPONENT_BOUND
    if shape_ok:
        print(f"\n  ⚠ the measured exponent is INSIDE the class's bound — the shape screen does "
              f"NOT refute\n     this candidate, and the verdict must rest on size alone.")
    else:
        print(f"\n  ⛔ on AG4's three fixed-⅓-oct centres every adjacent pair exceeds the bound "
              f"(weakest\n     {min(pair):.3f} vs {SINGLE_POLE_EXPONENT_BOUND:.3f}) — the deficit "
              f"steepens FASTER than any moving single pole can, so the\n     whole 'a capacitance "
              f"grows with drive' class is refuted on SHAPE, with no size\n     argument and no "
              f"threshold.")
        print(f"  ⛔ BUT DO NOT QUOTE THAT PHRASING (s141).  The pair statistic is not scale-free "
              f"and the\n     deficit does NOT beat the bound POINTWISE on a finer surface "
              f"(weakest ⅓-oct pair −0.117).\n     Quote GATE AL's ENDPOINT exponent over the "
              f"rising limb instead: > 2 at 5/5 half-widths,\n     smallest 2.530 — the statistic "
              f"this bound EXACTLY implies.  The class refutation stands\n     on THAT reading, "
              f"not on this one.  See the docstring's s141 correction block.")
    print(f"  ⚠ n = {len(rows4)} centres (AG4's own membership).  A bound the class must satisfy "
          f"and a\n    measurement that exceeds it — not a fit.")

    out["aj2"] = {"gm": gm, "z_drain_ohm": zd_at, "A": a_at, "miller_factor": 1 + a_at,
                  "cin_datasheet_pf": cin_at * 1e12, "required_pf":
                      {k: (None if v is None else v * 1e12) for k, v in req.items()},
                  "ceiling_pf": J201_CIN_CEILING_PF, "dtilt_at_ceiling": float(d_ceiling),
                  "reach": float(reach), "sign_ok": bool(sign_ok), "rows": rows,
                  "exponent": expo, "exponent_pairs": pair,
                  "exponent_bound": SINGLE_POLE_EXPONENT_BOUND,
                  "shape_admissible": bool(shape_ok), "n_centres": len(rows4),
                  "miller_split_drain_pole_hz": float(f_out),
                  "miller_split_zero_hz": float(f_zero)}
    return reach, sign_ok, shape_ok, expo, min(pair)


# ---------------------------------------------------------------------------
# AJ3 — candidate 2: IC2_A's GBW and slew
# ---------------------------------------------------------------------------
def gate_aj3(f0, out):
    print("\n" + "-" * 96)
    print("AJ3  CANDIDATE 2 — IC2_A's GBW and slew  (AF2/AF3 re-run PRE-clipper)")
    print("-" * 96)
    gain_max = 1.0 + D_R15 / (D_R17 + D_RDRIVE_MAXGAIN + D_R32)
    ft_req = f0 * gain_max
    short = AF.TL07X_GBW_MIN / ft_req
    print(f"  GBW.  IC2_A's closed-loop gain at DRIVE max is 1 + R15/(R17+R32) = {gain_max:.1f},")
    print(f"  so its own gain-bandwidth pole sits at ft/{gain_max:.1f}.  To put that pole ON the")
    print(f"  {f0:.0f} Hz vertex the part would need ft = {ft_req / 1e3:.1f} kHz, against "
          f"{AF.TL07X_GBW_MIN / 1e6:.1f} MHz min spec")
    print(f"  ⇒ {short:.1f}x short even at the WORST part TI sells.")
    print(f"\n  ⭐⭐ BUT THE SIZE ROW IS NOT THE ARGUMENT, AND IT IS NOT NEW.  AF2 established the")
    print(f"     structural half and it is a property of the PART, not of which stage it sits in:")
    print(f"     **gain-bandwidth is a SMALL-SIGNAL parameter.**  An op-amp in its linear region")
    print(f"     does not lose GBW as the signal grows; the large-signal limit is SLEW, a rate")
    print(f"     limit and not a bandwidth reduction.  ⇒ there is no amplitude at which this")
    print(f"     lever moves AT ALL, at IC2_A exactly as at the Sallen-Keys.  INHERITED, not")
    print(f"     re-derived.")

    # ---- slew: the harshest waveform IC2_A can be ASKED to produce, per AF3's construction
    print(f"\n  SLEW.  Session 138 asked for this specifically because the pre-clipper swing is")
    print(f"  larger.  Full-rail square wave DEMANDED at IC2_A's output, shaped by its own")
    print(f"  closed loop (R15 || C10 -> corner "
          f"{1.0 / (2 * np.pi * D_R15 * D_C10) / 1e3:.2f} kHz), normalised so the peak just")
    print(f"  reaches the rail.  Rails from FitParams.h: railNeg {AF.RAIL_NEG:.2f} V, railPos "
          f"{AF.RAIL_POS:.2f} V.\n")
    n_h = np.arange(1, 2001, 2)

    def rate_at(fq):
        """max |dV/dt| (V/us) of a full-rail square wave of fundamental fq at IC2_A's output.

        Vectorised as one matmul rather than a per-harmonic Python loop: the root-find below
        calls this ~60 times, and the loop form made a single gate run take 61 s.  The waveform
        and its derivative are both evaluated in closed form (d/dt of each term is known), so no
        finite difference is taken either.
        """
        fn = n_h * fq
        an = 4.0 / (np.pi * n_h)
        h = np.atleast_1d(EQ.drive_stage_tf(fn, D_RDRIVE_MAXGAIN, R15=D_R15, C10=D_C10,
                                            R17=D_R17, R32=D_R32))
        t = np.linspace(0.0, 1.0 / fq, 6001)
        basis = np.exp(2j * np.pi * np.outer(fn, t))
        coef = an * h
        y = np.real(coef @ basis)
        dy = np.real((coef * 2j * np.pi * fn) @ basis)
        pk = float(np.max(np.abs(y)))
        if pk <= 0.0:
            _die(f"AJ3 — the shaped square wave has zero peak at f0 = {fq} Hz; the normalisation "
                 f"is undefined and the rate would be fiction.")
        return float(np.max(np.abs(dy)) * (AF.RAIL_MAX / pk) / 1e6)

    print("     f0 Hz    IC2_A out (V/us)   margin vs 8 V/us")
    rows = []
    for fq in (100, 250, 500, 1000, 2000, 3000, 5000, 8000, 12000, 16000, 20000):
        r = rate_at(fq)
        rows.append({"f0": fq, "v_per_us": r})
        print(f"    {fq:6d}    {r:16.4f}   {AF.TL07X_SR_MIN / r:12.1f}x")

    # ⚠ A "worst rate over the sweep" figure is set by wherever the sweep STOPS -- the rate keeps
    # climbing with f0, so quoting it would make the verdict an artefact of the last table row.
    # The two numbers that are NOT endpoint-dependent are (i) the rate at the vertex, which is
    # where item 6's target lives, and (ii) the fundamental at which slew would first engage.
    r_vertex = rate_at(f0)
    margin_vertex = AF.TL07X_SR_MIN / r_vertex
    f_cross = solve_required(rate_at, AF.TL07X_SR_MIN, 100.0, 400.0e3)
    print(f"\n  ⚠ the WORST row is set by where this sweep STOPS — the rate climbs with f0 — so")
    print(f"    the verdict is quoted on the two endpoint-INDEPENDENT numbers instead:")
    print(f"\n  rate at the {f0:.0f} Hz vertex        : {r_vertex:.3f} V/us  "
          f"-> {margin_vertex:.0f}x margin at the MIN-spec part")
    if f_cross is None:
        print(f"  fundamental at which slew engages : NONE below 400 kHz")
    else:
        print(f"  fundamental at which slew engages : {f_cross / 1e3:.1f} kHz  "
              f"({f_cross / f0:.1f}x the vertex)")
    print(f"  TL07x slew rate                   : {AF.TL07X_SR_TYP:.0f} V/us typ, "
          f"{AF.TL07X_SR_MIN:.0f} V/us min")

    slew_reaches = margin_vertex <= 1.0
    if slew_reaches:
        print(f"\n  ⚠ REACHES: IC2_A slews at the vertex, so slew limiting must be modelled")
        print(f"     before it can be dismissed.")
    else:
        print(f"\n  ⛔ REFUTED AT THE VERTEX: {margin_vertex:.0f}x margin at 2935 Hz, on a "
              f"FULL-RAIL SQUARE\n     WAVE — a bound, not a signal.  ⚠ And state the honest "
              f"caveat: the margin here is far\n     tighter than AF3's at the Sallen-Keys "
              f"(the pre-clipper swing IS larger, exactly as\n     s138 expected), and on that "
              f"same bound the stage WOULD slew above "
              f"{'-' if f_cross is None else f'{f_cross / 1e3:.0f} kHz'}"
              f" — which is\n     out of band and out of reach of a bass preamp, but it is not "
              f"a 50x margin and should\n     not be quoted as one.")
    out["aj3"] = {"gain_max": gain_max, "ft_required_hz": ft_req, "gbw_shortfall": short,
                  "gbw_structural_refutation": "inherited from AF2 — GBW is small-signal",
                  "slew_at_vertex_v_per_us": r_vertex, "slew_margin_at_vertex": margin_vertex,
                  "slew_cross_hz": (None if f_cross is None else float(f_cross)),
                  "slew_reaches": bool(slew_reaches), "rows": rows}
    return slew_reaches, margin_vertex, short, f_cross


# ---------------------------------------------------------------------------
# AJ4 — candidate 3: the GRUNT caps' voltage coefficient
# ---------------------------------------------------------------------------
def gate_aj4(f0, half, budget, need, out):
    print("\n" + "-" * 96)
    print("AJ4  CANDIDATE 3 — the GRUNT coupling caps' own voltage coefficient")
    print("-" * 96)
    caps = AI.grunt_caps()
    print(f"  On AI's at-clipper block, with the caps COMPOSED as Clipper::gruntCap() does")
    print(f"  (corrected s139 — clipC12/clipC13 are ADD-caps):")
    for nm in ("cut", "flat", "boost"):
        print(f"      {nm:<6s} {caps[nm] * 1e9:8.3f} nF")
    print(f"\n  A voltage coefficient makes C FALL with signal, so the mechanism's own direction")
    print(f"  is a REDUCTION in Cg.  d(tilt) at the vertex per fractional cap change:\n")
    print(f"  {'dC/C':>8s} " + " ".join(f"{nm:>14s}" for nm in ("cut", "flat", "boost")))
    base = {nm: AI.tilt_fine(AI.mech_db(AB.CLIP_A0, caps[nm]), f0, half) for nm in caps}
    tab = {}
    for frac in (-VCO_FILM, -0.01, -0.10, -VCO_X7R, -0.90):
        row = {nm: AI.tilt_fine(AI.mech_db(AB.CLIP_A0, caps[nm] * (1.0 + frac)), f0, half)
               - base[nm] for nm in caps}
        tab[f"{frac:g}"] = row
        tag = ("  <- film ceiling" if abs(frac + VCO_FILM) < 1e-12 else
               "  <- X7R ceramic ceiling" if abs(frac + VCO_X7R) < 1e-12 else "")
        print(f"  {100 * frac:7.1f}% " + " ".join(f"{row[nm]:+14.5f}"
                                                 for nm in ("cut", "flat", "boost")) + tag)

    lim = tab[f"{-0.90:g}"]
    x7r = tab[f"{-VCO_X7R:g}"]
    print(f"\n  ⚠ -90 % is NOT an operating point — it is a limit past any dielectric, quoted so")
    print(f"    the ceiling holds for any part that could be fitted.")

    # Sign + GRUNT-consistency, with the target as a VARIABLE (AB5).
    print(f"\n  {'GRUNT':<6s} {'mech @X7R':>11s} {'mech @limit':>13s} {'defect':>9s} "
          f"{'sign ok?':>9s} {'reach':>9s}")
    reach, signok = {}, {}
    for nm in ("cut", "flat", "boost"):
        m, d = lim[nm], need[nm]
        ok = (m < 0) == (d < 0)
        r = (m / d) if (ok and d != 0) else 0.0
        reach[nm], signok[nm] = float(r), bool(ok)
        print(f"  {nm:<6s} {x7r[nm]:+11.5f} {m:+13.5f} {d:+9.3f} {str(ok):>9s} "
              f"{100 * r:8.2f}%")
    n_ok = sum(signok.values())
    worst_reach = max(reach.values())

    # The GRUNT-consistency screen: does the mechanism's PATTERN across positions match the
    # defect's?  ⚠⚠ Normalise by the MAGNITUDE of the cut position, never by the signed value:
    # dividing each side by its own signed cut entry forces BOTH to +1.000 there and destroys
    # the sign difference the screen exists to see -- which is what a first draft of this gate
    # did, printing a reassuring 0.002 agreement at `flat` between a mechanism and a defect of
    # OPPOSITE sign.  (`a classifier's verdict must be a comparison against the target`, AB5.)
    mech_pat = {nm: lim[nm] / abs(lim["cut"]) for nm in caps}
    def_pat = {nm: need[nm] / abs(need["cut"]) for nm in caps}
    print(f"\n  GRUNT-CONSISTENCY (item 6's 4th gate) — pattern across positions, re |cut|:")
    print(f"    mechanism : " + "  ".join(f"{nm} {mech_pat[nm]:+7.3f}"
                                          for nm in ("cut", "flat", "boost")))
    print(f"    defect    : " + "  ".join(f"{nm} {def_pat[nm]:+7.3f}"
                                          for nm in ("cut", "flat", "boost")))
    pat_worst = max(abs(mech_pat[nm] - def_pat[nm]) for nm in ("cut", "flat", "boost"))
    print(f"    worst departure : {pat_worst:.3f}   (a sign flip alone costs >= 2.000 at cut)")
    out["aj4"] = {"caps": caps, "table": tab, "limit": lim, "x7r": x7r, "reach": reach,
                  "sign_ok": signok, "n_sign_ok": n_ok, "worst_reach": float(worst_reach),
                  "mech_pattern": mech_pat, "defect_pattern": def_pat,
                  "pattern_worst_departure": float(pat_worst)}
    return n_ok, worst_reach, pat_worst


# ---------------------------------------------------------------------------
# AJ5 — the computed verdict
# ---------------------------------------------------------------------------
def gate_aj5(c1, c2, c3, out):
    reach1, sign1, shape1, expo, expo_min = c1
    slew_reaches, margin, gbw_short, f_cross = c2
    n_ok3, reach3, pat3 = c3

    print("\n" + "-" * 96)
    print("AJ5  VERDICT — each candidate against item 6's four pre-registered gates")
    print("-" * 96)

    v = {}
    # Candidate 1
    if reach1 >= 1.0 and sign1 and shape1:
        v["j201_miller"] = ("REACHES — the J201 gate capacitance can carry the budget with the "
                            "right sign and an admissible shape; this is a CANDIDATE")
    elif not shape1:
        v["j201_miller"] = (f"REFUTED ON SHAPE AND SIZE — the deficit steepens as f^{expo:.2f} "
                            f"(this gate's weakest adjacent pair f^{expo_min:.2f}; ⛔ s141 — quote "
                            f"GATE AL's ENDPOINT exponent > 2 at 5/5 half-widths, smallest 2.530, "
                            f"NOT the pair column), above the exact f^2 bound "
                            f"every moving single pole obeys; and even at a capacitance ceiling "
                            f"{J201_CIN_CEILING_PF / J201_CISS_MAX_PF:.1f}x the part's datasheet "
                            f"maximum it reaches {100 * reach1:.2f}% of the budget")
    else:
        v["j201_miller"] = (f"REFUTED ON SIZE — {100 * reach1:.2f}% of the budget at a "
                            f"capacitance ceiling well past the part")
    # Candidate 2
    if slew_reaches:
        v["ic2a"] = "REACHES ON SLEW — slew limiting is engaged at IC2_A and must be modelled"
    else:
        xs = "never" if f_cross is None else f"only above {f_cross / 1e3:.0f} kHz"
        v["ic2a"] = (f"REFUTED — GBW is a SMALL-SIGNAL parameter so no amplitude moves it "
                     f"(AF2, inherited; and {gbw_short:.0f}x short on size besides), and slew "
                     f"carries a {margin:.0f}x margin AT THE VERTEX on a full-rail square wave, "
                     f"engaging {xs} — out of band for a bass preamp, but a far tighter margin "
                     f"than AF3's post-clipper one and not to be quoted as 50x")
    # Candidate 3
    if n_ok3 == 3 and reach3 >= 1.0:
        v["grunt_vco"] = ("REACHES — the GRUNT caps' voltage coefficient has the right sign "
                          "everywhere and is large enough")
    elif n_ok3 == 0:
        v["grunt_vco"] = ("REFUTED ON SIGN — a falling coupling cap pushes the tilt the WRONG "
                          "way at every GRUNT position, so no dielectric can carry it")
    elif n_ok3 == 3:
        v["grunt_vco"] = (f"RIGHT SIGN EVERYWHERE, TOO SMALL — {100 * reach3:.2f}% of the "
                          f"requirement at its best position, at a cap reduction past any "
                          f"dielectric")
    else:
        v["grunt_vco"] = (f"REFUTED — right sign at only {n_ok3} of 3 GRUNT positions, best "
                          f"reach {100 * reach3:.2f}% at a limit past any dielectric, and the "
                          f"per-position pattern departs from the defect's by {pat3:.2f}")

    for k in ("j201_miller", "ic2a", "grunt_vco"):
        print(f"  {k:<14s} : {v[k]}")

    n_reach = sum(1 for s in v.values() if s.startswith("REACHES"))
    print("\n" + "-" * 96)
    if n_reach == 0:
        joint = ("ALL THREE REFUTED — with AF7's five post-clipper carriers and AI's at-clipper "
                 "`a0`, EVERY named carrier on BOTH sides of the clipper is now refuted, while "
                 "the deficit stays measured, sized and twice-localised.  Session 138's `NEXT` "
                 "#2 fires: the pre/at-clipper FRAME is now the thing in question, and the "
                 "honest next step is to ask what is left rather than to widen a bound.")
    else:
        joint = (f"{n_reach} of 3 candidates REACH — the pre-clipper frame survives and the "
                 f"survivor(s) must now be gated on shape and on GRUNT-sign consistency.")
    print(f"  {joint}")
    print("\n  ⚠ SCOPE — what is refuted is a list of NAMED carriers, not the existence of a")
    print("    mechanism.  Nothing here touches the bridged-T half of AB6, and nothing here")
    print("    claims the deficit is unreal: AG3/AG5 measured it at 1.72x the requirement.")
    out["aj5"] = {"per_candidate": v, "n_reach": n_reach, "joint": joint}
    return v, joint


def main():
    ap = argparse.ArgumentParser(description="GATE AJ — the three unscreened pre-clipper "
                                             "candidates")
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
        _die(f"AJ — the stored GATE AI report's defect covers {sorted(need)}, not all three GRUNT "
             f"positions; the consistency screen this gate rests on is not evaluable.")

    print("=" * 96)
    print("GATE AJ — the three unscreened PRE-CLIPPER candidates for item 6's treble half")
    print("=" * 96)
    print(f"  vertex, window, budget and the DEFECT are READ from stored reports, never "
          f"transcribed:")
    print(f"      vertex {f0:.1f} Hz,  window +-{half} oct        [{os.path.basename(a.ag)}]")
    print(f"      AH7 budget {budget:+.3f} dB/oct, AG5 available {avail:+.3f} dB/oct"
          f"   [{os.path.basename(a.ah)}]")
    print(f"      defect per GRUNT: " + ", ".join(f"{k} {need[k]:+.3f}"
                                                  for k in ("cut", "flat", "boost"))
          + f"   [{os.path.basename(a.ai)}]")
    print(f"  ⚠ PREMISE, printed every run: AF2's GBW refutation is INHERITED here, not")
    print(f"    re-derived — it is a statement about the PART (gain-bandwidth is small-signal),")
    print(f"    so it transfers from the Sallen-Keys to IC2_A unchanged.  AF3's SLEW number does")
    print(f"    NOT transfer, and is re-measured at IC2_A's own node below.")

    out = {"ag_report": a.ag, "ah_report": a.ah, "ai_report": a.ai, "vertex_hz": f0,
           "half_oct": half, "budget": budget, "available": avail, "defect": need}

    gate_aj1(f0, half, out)
    c1 = gate_aj2(f0, half, budget, avail, ag["ag4"], out)
    c2 = gate_aj3(f0, out)
    c3 = gate_aj4(f0, half, budget, need, out)
    gate_aj5(c1, c2, c3, out)

    if a.json:
        os.makedirs(os.path.dirname(os.path.abspath(a.json)), exist_ok=True)
        with open(a.json, "w") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"\n  -> {a.json}")
    print("\n" + "=" * 96)
    print("GATE AJ: all guards passed.  AJ2-AJ5 are readable.")
    print("=" * 96)
    return 0


if __name__ == "__main__":
    sys.exit(main())
