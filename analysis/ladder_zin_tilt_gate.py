#!/usr/bin/env python3.11
"""GATE AS — a DRIVE-DEPENDENT TREBLE-LADDER `Zin` as open-work item 6's tilt carrier.

    /opt/homebrew/bin/python3.11 analysis/ladder_zin_tilt_gate.py

⚠⚠ WHY THIS GATE EXISTS.  Session 149's GATE AO mechanised session 148's audit ("for every gate
that screened a stage, diff the parameters its mechanism function ACCEPTS against the ones it
SWEPT") and found ONE genuinely unscreened lever on the pre-clipper side: `zin`, the fourth
argument of GATE AK's own `drain_db(gm, ro, rq2, zin)`, classified KA-ONLY — its only non-baseline
expression anywhere is `inf`, inside AK's own known-answer sub-gate.  AO1c's exact sensitivity
identity then sized it:

    d ln Zd / d ln Zin  +  d ln Zd / d ln Zout  ==  1     (exactly)

and at the shipped ladder it reads S_zin 0.836 / S_zout 0.168, i.e. **the LOAD side of the drain
node's divider carries 4.97x the lever of the SOURCE side** — where every carrier screened so far
acts (AK's gm-through-`Zout`, AJ's moving-pole class, AN's `ro`/`rq2`).  AN3b, written as a
refutation, read as a SPECIFICATION points here.

⚠ AO deliberately did NOT screen it, and said so.  This gate does.

⭐⭐ AND IT STARTS FROM THE SHAPE QUESTION, NOT FROM A COMPONENT LIST — AO's own instruction.  The
ladder is all-real-pole (GATE AM censused it on the stamps), and gate 5's `d ln|dT|/d ln f <= 2`
bound applies exactly to a SINGLE real pole whose corner moves.  It does NOT automatically apply to
a perturbation of a MULTI-element network, because such a perturbation moves every pole and zero at
once and terms of opposite sign can cancel.  So the honest question is AO's: *which perturbation of
this network can rise as f^+2.8 AT ALL* — and then, of those, which one also reaches.

⚠⚠ THE TRAP THIS GATE HAD TO AVOID, AND IT FIRED ON THE FIRST DRAFT.  Read on the endpoint exponent
alone, 2 of 660 single-element probes clear the pole bound and one reads **+4.14** — which would
have been published as "the class is SHAPE-ADMISSIBLE".  Its tilt change CROSSES ZERO inside the
limb (+0.00017 at 1348 Hz, negative everywhere above), so the endpoint ratio is divided by a number
that is passing through zero.  That is exactly the artefact AL3 guarded the deficit against
("single-signed at 12/12, so no log below is a zero-crossing artefact") and the guard had never
been pointed at a MECHANISM.  Every exponent here is therefore reported with two validity columns —
SINGLE-SIGNEDNESS and MONOTONICITY across the limb — and the graded frontier uses only probes that
carry both, because AL4's limb is the deficit's RISING limb by construction and a carrier whose
|dT| turns over inside it cannot be carrying it whatever its endpoints say.

WHAT IT DOES NOT CLAIM
  * The frontier is a SEARCH over a finite probe set (single elements at 20 sizes x 3 ATTACK
    throws, plus all pairs of the six highest-lever elements on a 12x12 grid), not a theorem.
    AS4's linearised SVD is what covers the small-perturbation directions the grid cannot enumerate.
  * Nothing is graded against hardware; nothing renders; no constant moves; the baseline is
    untouched.
  * "A drive-dependent ladder Zin" names no physical carrier and this gate does not supply one —
    it screens the reachable set, which is the stronger thing to do first (AO's own point).
"""
import argparse
import contextlib
import io
import itertools
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import parallel                          # noqa: E402
import at_clipper_tilt_gate as AI        # noqa: E402  FINE, tilt_fine
import pre_clipper_tilt_gate as AJ       # noqa: E402  ladder_zin, ladder_kwargs, divergence
import j201_shaper_tilt_gate as AK       # noqa: E402  drain_db
import bt_pair_shape_gate as AB          # noqa: E402  _read_fitparam

with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ            # noqa: E402  jfet_source_z

AG_REPORT = "analysis/reports/s135_drive_tilt.json"
AH_REPORT = "analysis/reports/s137_vertex_curvature.json"
AL_REPORT = "analysis/reports/s141_deficit_exponent.json"
OUT_JSON = "analysis/reports/s155_ladder_zin_tilt.json"

SINGLE_POLE_EXPONENT_BOUND = AJ.SINGLE_POLE_EXPONENT_BOUND     # 2.0, exact

# AL4's exponent across its five half-widths runs 2.53-2.90.  The bar MOST FAVOURABLE TO THE
# CANDIDATE is the smallest (AJ2c's discipline: gate on the weakest reading), and the primary is
# quoted beside it so a reader can see both.
AL4_WEAKEST_EXPONENT = 2.530

# Single-element probe sizes.  Deliberately spans far past anything physical: a limit is a CEILING
# for any excursion (AN2's construction), and a class that cannot reach at x1e6 cannot reach at all.
FRACS = (1.0001, 1.001, 1.01, 1.1, 1.5, 2.0, 5.0, 10.0, 1.0e3, 1.0e6,
         0.9999, 0.999, 0.99, 0.9, 0.667, 0.5, 0.2, 0.1, 1.0e-3, 1.0e-6)

# The pair search runs over the highest-|lever| elements only — cancellation between two big levers
# is the one way a probe search could find a steep-AND-large point that the singles miss.  Chosen
# from AS2's own measured lever column, printed there, NOT from intuition.
PAIR_FRACS = (1.0e-3, 0.1, 0.3, 0.5, 0.8, 0.95, 1.05, 1.25, 2.0, 5.0, 10.0, 1.0e3)
N_PAIR_ELEMS = 6

# Physical drift ceilings, imported in spirit from AJ4's own screen and quoted at the pessimistic
# end so the verdict survives a part-spread argument.
VCO_FILM = AJ.VCO_FILM      # 0.1 %  — film cap voltage coefficient
VCO_X7R = AJ.VCO_X7R        # 50 %   — X7R ceramic, deliberately generous
R_TEMPCO = 0.01             # 1 %    — a metal-film resistor over any realistic self-heating

KA_TOL_TILT = 1e-9
KA_TOL_EXACT = 0.0
KA_TOL_EXP = 0.05

POSITIONS = ("flat", "boost", "cut")


def _die(msg):
    print(f"\n⛔ GATE AS REFUSES: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# The block, and the windowed-subset evaluation the search rests on
# ---------------------------------------------------------------------------
_CTX = {}


def _ctx():
    """Per-process context.  Built lazily so `pmap_cpu`'s spawned workers each build their own.

    ⚠ Module-level mutable state shared across THREADS is s133's documented race; this is a
    PROCESS pool, so each worker has its own copy and there is nothing to leak.  The context is
    plain derived data (window indices, baseline tilts) — no injection flag lives here.
    """
    if not _CTX:
        al = json.load(open(os.path.join(os.path.dirname(HERE), AL_REPORT)))
        ah = json.load(open(os.path.join(os.path.dirname(HERE), AH_REPORT)))
        ag = json.load(open(os.path.join(os.path.dirname(HERE), AG_REPORT)))
        prim = al["al4"]["primary"]
        _CTX["centres"] = np.array(prim["centres"], dtype=float)
        _CTX["deficits"] = np.array(prim["deficits"], dtype=float)
        _CTX["half"] = ah["primary_half_oct"]
        _CTX["f0"] = ag["vertex_hz"]
        _CTX["budget"] = ah["ah7"]["tilt_max_db_oct"]
        _CTX["gm"] = AB._read_fitparam("jfetGm")
        _CTX["ro"] = AB._read_fitparam("jfetRo")
        _CTX["rq2"] = AB._read_fitparam("jfetRq2")
        _CTX["idx"] = window_indices(_CTX["centres"], _CTX["half"])
        _CTX["base"] = {p: tilts(AJ.ladder_kwargs(p), p) for p in POSITIONS}
    return _CTX


def window_indices(centres, half):
    """The FINE indices any of the tilt windows actually reads.

    `tilt_fine` masks `AI.FINE` to |log2(f/f0)| <= half around each centre, so every index outside
    the union of those windows is NEVER read — which is what makes AS1b's subset evaluation
    BIT-IDENTICAL rather than merely close, and the search 3.7x cheaper.
    """
    lg = np.log2(np.asarray(AI.FINE)[:, None] / np.asarray(centres)[None, :])
    return np.where(np.any(np.abs(lg) <= half, axis=1))[0]


def drain_tilts(kw, position, idx=None, full=False):
    """Tilt of the drain-node block at each of AL4's limb centres, for one ladder element set.

    `full=True` evaluates on the whole of AI.FINE (the reference path AS1b checks against);
    otherwise only the window indices are computed and scattered into a full-length array, which
    `tilt_fine` then masks exactly as it always did.
    """
    c = _ctx()
    if full:
        z = AJ.ladder_zin(AI.FINE, position=position, which=kw)
        db = AK.drain_db(c["gm"], c["ro"], c["rq2"], z)
    else:
        idx = c["idx"] if idx is None else idx
        fsub = np.asarray(AI.FINE)[idx]
        z = AJ.ladder_zin(fsub, position=position, which=kw)
        db = np.zeros(len(AI.FINE), dtype=float)
        db[idx] = AK.drain_db(c["gm"], c["ro"], c["rq2"], z, f=fsub)
    return np.array([AI.tilt_fine(db, f, c["half"]) for f in c["centres"]])


def tilts(kw, position):
    return drain_tilts(kw, position, full=False)


def endpoint_exponent(f, y):
    """AL4's own statistic — the one the pointwise real-pole bound EXACTLY implies when integrated
    over a limb, and the one AL4 established as the scale-free replacement for AJ2c's per-pair form.
    """
    f = np.asarray(f, dtype=float)
    y = np.abs(np.asarray(y, dtype=float))
    if y[0] <= 0.0 or y[-1] <= 0.0:
        return float("nan")
    return float(np.log(y[-1] / y[0]) / np.log(f[-1] / f[0]))


def shape_columns(d):
    """Everything needed to decide whether an endpoint exponent MEANS anything, per probe."""
    a = np.abs(d)
    n = int(d.size)
    return {"exponent": endpoint_exponent(_ctx()["centres"], d),
            "one_signed": int(max(np.sum(d > 0.0), np.sum(d < 0.0))),
            "n": n,
            "rising": int(np.sum(np.diff(a) > 0.0)),
            "n_step": n - 1}


def probe(job):
    """One perturbation: (position, (element, ...), (fraction, ...)) -> a scored row."""
    position, elems, fracs = job
    c = _ctx()
    kw0 = AJ.ladder_kwargs(position)
    kw = dict(kw0)
    for e, fr in zip(elems, fracs):
        kw[e] = kw0[e] * fr
    d = tilts(kw, position) - c["base"][position]
    if not np.all(np.isfinite(d)) or np.abs(d).min() <= 0.0:
        return None
    iv = int(np.argmin(np.abs(c["centres"] - c["f0"])))
    row = shape_columns(d)
    row.update(position=position, elems=list(elems), fracs=list(fracs),
               d_vertex=float(d[iv]),
               reach=float(abs(d[iv] / c["budget"])) if c["budget"] else 0.0,
               sign_ok=bool((d[iv] < 0.0) == (c["budget"] < 0.0)),
               d_first=float(d[0]), d_last=float(d[-1]),
               # THE THIRD AXIS.  A probe's SIZE is not only how far it moves the tilt — it is
               # also how far the ELEMENT had to move to do it, and a drive-dependent mechanism
               # can only move an element by a physically bounded amount (AJ4's own ceilings).
               # ⚠ Measured as a FOLD CHANGE, max(fr, 1/fr), not as |fr - 1|: the latter saturates
               # at 1.0 for every shrinking element, so it reads x0.1 and x0.001 as the same
               # perturbation when they are three decades apart.
               drift=float(max(max(fr, 1.0 / fr) for fr in fracs)),
               shape=[float(x) for x in d])
    return row


def clean_shape(row):
    """A probe whose endpoint exponent is READABLE and whose shape can carry the deficit's limb.

    Two conditions, both forced on this gate by prior sessions rather than chosen here:
      * SINGLE-SIGNED across the limb — AL3's guard, without which the endpoint ratio is a
        zero-crossing artefact (and on the first draft it was, at the top of the exponent table);
      * MONOTONE RISING in |dT| — AL4 splits the deficit at the argmin of |D| and grades the RISING
        limb, so a mechanism that turns over inside that limb is not tracking it.
    """
    return (row["one_signed"] == row["n"]) and (row["rising"] == row["n_step"])


# ---------------------------------------------------------------------------
# AS1 — known answers
# ---------------------------------------------------------------------------
def gate_as1(out):
    print("\n" + "-" * 96)
    print("AS1  KNOWN ANSWERS")
    print("-" * 96)
    c = _ctx()
    ok = {}

    # (a) THE LICENCE — the tilt operator is LINEAR on log-magnitude, so every block that does not
    #     depend on the perturbed parameter cancels EXACTLY from the tilt CHANGE (AI1c).  That is
    #     what lets this gate model the drain node alone and no part of the chain downstream of it.
    #     Asserted against a deliberately wild fixed block, not argued.
    s = 2j * np.pi * np.asarray(AI.FINE)
    fixed = (1.0 + s / (2 * np.pi * 2500.0)) / (
        (1.0 + s / (2 * np.pi * 900.0)) * (1.0 + s / (2 * np.pi * 3300.0)) ** 2)
    fdb = 20.0 * np.log10(np.abs(fixed))
    kw0 = AJ.ladder_kwargs("flat")
    kwp = dict(kw0)
    kwp["C5"] = kw0["C5"] * 0.5

    def _t_with(kw, extra):
        z = AJ.ladder_zin(AI.FINE, position="flat", which=kw)
        db = AK.drain_db(c["gm"], c["ro"], c["rq2"], z) + extra
        return np.array([AI.tilt_fine(db, f, c["half"]) for f in c["centres"]])

    bare = _t_with(kwp, 0.0) - _t_with(kw0, 0.0)
    withf = _t_with(kwp, fdb) - _t_with(kw0, fdb)
    cancel = float(np.max(np.abs(withf - bare)))
    ok["licence"] = cancel < KA_TOL_TILT
    print(f"  (a) LICENCE — a wild fixed block cancels from the tilt CHANGE : {cancel:.3e} dB/oct "
          f"(bar {KA_TOL_TILT:.0e})   {'OK' if ok['licence'] else 'FAIL'}")

    # (b) THE WINDOWED-SUBSET EVALUATION, which the whole 7000-probe search rests on.  `tilt_fine`
    #     reads only the indices inside its own windows, so computing the ladder anywhere else is
    #     wasted work — and the claim that it is EXACTLY wasted is a measurement, not an argument.
    #     Asserted at the baseline AND at a perturbed set, and the bar is BIT-IDENTITY, not a
    #     tolerance: anything looser would hide a window that had drifted by one index.
    sub_errs = []
    for pos, kw in (("flat", kw0), ("flat", kwp), ("cut", AJ.ladder_kwargs("cut"))):
        a = drain_tilts(kw, pos, full=True)
        b = drain_tilts(kw, pos, full=False)
        sub_errs.append(float(np.max(np.abs(a - b))))
    worst_sub = max(sub_errs)
    ok["subset"] = worst_sub <= KA_TOL_EXACT
    print(f"  (b) SUBSET evaluation is BIT-IDENTICAL to the full grid  : {worst_sub:.3e} dB/oct "
          f"(bar {KA_TOL_EXACT:.0e})   {'OK' if ok['subset'] else 'FAIL'}")
    print(f"      {len(c['idx'])} of {len(AI.FINE)} FINE points are inside a tilt window "
          f"({len(AI.FINE) / len(c['idx']):.2f}x cheaper)")

    # (c) THE DIVERGENCE GUARD (AM1a, and s149's finding that AJ/AK/AN all lacked it).  A gate that
    #     computes Zin from the DRAWN defaults still runs and still prints plausible numbers; the
    #     only thing that catches it is asserting the two element sets actually DIFFER.
    n_moved, n_tot, moved = AJ.ladder_divergence("flat")
    ok["divergence"] = n_moved > 0
    print(f"  (c) shipped vs drawn ladder differ in                     : {n_moved} of {n_tot} "
          f"values   {'OK' if ok['divergence'] else 'FAIL'}   (element set: {AJ.LADDER_VALS!r})")
    if not ok["divergence"]:
        _die("AS1c — the shipped and drawn treble ladders are identical, so this gate cannot tell "
             "which one it is screening.  That is the exact defect GATE AO found in three gates.")

    # (d) PROBE INDEPENDENCE of the Zin extraction (AJ1d), WITH its blindness stated rather than
    #     left to be found: both sides share the ELEMENT SET as input, so this validates the
    #     EXTRACTION and can say nothing about whether the values are the shipped ones (AM1a/AO).
    z1 = AJ.ladder_zin(AI.FINE, position="flat", zs_probe=1.0e3)
    z2 = AJ.ladder_zin(AI.FINE, position="flat", zs_probe=47.0e3)
    rel = float(np.max(np.abs(z1 - z2) / np.abs(z1)))
    ok["probe"] = rel < 1e-9
    print(f"  (d) Zin is probe-independent (1k vs 47k)                  : {rel:.3e} rel   "
          f"{'OK' if ok['probe'] else 'FAIL'}   ⚠ validates the EXTRACTION, not the VALUE SET")

    # (e) THE ESTIMATOR DISCRIMINATES.  AL1's discipline: an exponent statistic that BIASES upward
    #     would manufacture this gate's whole subject.  Fed analytic curves of KNOWN exponent — a
    #     single real pole's own tilt shape (the class bound, exactly 2 in its f << fp regime) and
    #     a pure f^3 — it must return them, so "the mechanism reads below 2" is a measurement and
    #     not an artefact of the reader.
    f = c["centres"]
    fp = 40.0e3                       # far above the limb -> the pole's tilt change is ~ f^2
    u = (f / fp) ** 2
    pole_curve = -6.0206 * u / (1.0 + u)
    e_pole = endpoint_exponent(f, pole_curve)
    e_cube = endpoint_exponent(f, (f / f[0]) ** 3)
    ok["estimator"] = (abs(e_pole - 2.0) < KA_TOL_EXP) and (abs(e_cube - 3.0) < 1e-9)
    print(f"  (e) ESTIMATOR on injected KNOWN exponents                 : single pole "
          f"{e_pole:+.4f} (true 2), f^3 {e_cube:+.4f} (true 3)   "
          f"{'OK' if ok['estimator'] else 'FAIL'}")

    # (f) AL4 REPRODUCTION (AN3's guard).  Recomputing AL4's endpoint exponent from AL4's OWN
    #     stored centres must return AL4's stored value, or nothing below is a like-for-like
    #     comparison with the deficit.
    al = json.load(open(os.path.join(os.path.dirname(HERE), AL_REPORT)))
    stored = al["al4"]["primary"].get("endpoint_exponent")
    e_def = endpoint_exponent(c["centres"], c["deficits"])
    ok["al4"] = stored is not None and abs(e_def - stored) < 1e-9
    print(f"  (f) AL4's endpoint exponent reproduces from its own data  : {e_def:+.6f} vs stored "
          f"{stored:+.6f}   {'OK' if ok['al4'] else 'FAIL'}")
    if not ok["al4"]:
        _die(f"AS1f — recomputing AL4's endpoint exponent gives {e_def:.6f} against its stored "
             f"{stored}.  The import is not reproducing the source gate.")

    # (g) THE DEFICIT'S OWN VALIDITY COLUMNS, printed here so the mechanism's are read against
    #     something rather than against nothing.
    dcols = shape_columns(c["deficits"])
    print(f"  (g) the DEFICIT itself: exponent {e_def:+.4f}   single-signed "
          f"{dcols['one_signed']}/{dcols['n']}   |D| rising {dcols['rising']}/{dcols['n_step']}")

    failed = [k for k, v in ok.items() if not v]
    if failed:
        _die(f"AS1 — known answers failed: {', '.join(failed)}.  Nothing below is readable.")
    print(f"\n  all {len(ok)} known answers hold.")
    out["as1"] = {"cancel": cancel, "subset_worst": worst_sub, "n_idx": int(len(c["idx"])),
                  "divergence_moved": n_moved, "divergence_total": n_tot,
                  "moved": {k: list(v) for k, v in moved.items()},
                  "probe_rel": rel, "e_pole": e_pole, "e_cube": e_cube,
                  "e_deficit": e_def, "e_deficit_stored": stored,
                  "deficit_columns": dcols, "ok": ok}
    return e_def, dcols


# ---------------------------------------------------------------------------
# AS2 — SIZE.  The lever is real, and that is the first thing that makes this
#              class different from every carrier screened before it.
# ---------------------------------------------------------------------------
def gate_as2(out):
    print("\n" + "-" * 96)
    print("AS2  SIZE — is this lever big enough to matter?  (it is: the first one that is)")
    print("-" * 96)
    c = _ctx()
    iv = int(np.argmin(np.abs(c["centres"] - c["f0"])))
    print(f"  graded at AL4 centre {c['centres'][iv]:.1f} Hz (nearest the {c['f0']:.1f} Hz vertex)")
    print(f"  AH7's budget (position ceiling, IMPORTED) : {c['budget']:+.4f} dB/oct")

    # AO1c's identity, recomputed here at the shipped set so the specification this gate answers
    # is printed beside the answer.
    zout = EQ.jfet_source_z(AI.FINE, gm=c["gm"], ro=c["ro"], Rq2=c["rq2"], R6=AJ.J_R6, C3=AJ.J_C3)
    zin = AJ.ladder_zin(AI.FINE, position="flat")
    i = int(np.argmin(np.abs(np.asarray(AI.FINE) - c["f0"])))
    s_zin = abs(zout[i] / (zout[i] + zin[i]))
    s_zout = abs(zin[i] / (zout[i] + zin[i]))
    print(f"  AO1c at the vertex: S_zin {s_zin:.4f}  S_zout {s_zout:.4f}  "
          f"LOAD-side lever {s_zin / s_zout:.2f}x the source side")

    rows = []
    kw0 = AJ.ladder_kwargs("flat")
    elems = [k for k, v in kw0.items() if v != 0.0]
    print(f"\n  per-element lever, ATTACK 'flat', d(tilt)/d ln(element) and the reach of a 1 % drift:")
    print(f"  {'element':>9s} {'value':>12s} {'dT/dln':>12s} {'reach @1%':>11s} "
          f"{'reach @limits':>14s}")
    levers = {}
    for e in elems:
        kwp = dict(kw0)
        kwp[e] = kw0[e] * 1.001
        d = tilts(kwp, "flat") - c["base"]["flat"]
        lever = float(d[iv] / math.log(1.001))
        lim = []
        for fr in (1.0e6, 1.0e-6):
            kwl = dict(kw0)
            kwl[e] = kw0[e] * fr
            dl = tilts(kwl, "flat") - c["base"]["flat"]
            lim.append(abs(dl[iv] / c["budget"]))
        levers[e] = lever
        rows.append([e, kw0[e], lever, abs(0.01 * lever / c["budget"]), max(lim)])
    for e, v, lever, r1, rl in sorted(rows, key=lambda r: -abs(r[2])):
        print(f"  {e:>9s} {v:12.5g} {lever:+12.6f} {100 * r1:10.4f}% {100 * rl:13.3f}%")

    top = [e for e, _ in sorted(levers.items(), key=lambda kv: -abs(kv[1]))][:N_PAIR_ELEMS]
    print(f"\n  the {N_PAIR_ELEMS} highest-lever elements (AS3's pair search runs over these, "
          f"chosen from this measured column): {', '.join(top)}")

    # ⭐ THE TWO NUMBERS THAT MUST BE QUOTED TOGETHER.  At a LIMIT this class reaches far past the
    # budget — which is what makes it different from every carrier before it, and is AO4's lever
    # showing up as promised.  At a drift a mechanism could actually supply it does not, and that
    # is the same order as the classes already refuted.  Quoting either alone mis-states it.
    reach_1pct = max(abs(0.01 * lv / c["budget"]) for lv in levers.values())
    reach_limit = max(r[4] for r in rows)
    print(f"\n  ⭐ reach at a SINGLE-ELEMENT LIMIT (x1e6 / x1e-6) : {100 * reach_limit:.1f} % of the "
          f"budget — the first pre-clipper class that reaches at all")
    print(f"     reach at a 1 % drift of the best element       : {100 * reach_1pct:.4f} % — the "
          f"same order as AK (2.46 %) and AN (1.33 %) at THEIR limits")
    out["as2"] = {"s_zin": s_zin, "s_zout": s_zout, "load_lever": s_zin / s_zout,
                  "levers": levers, "pair_elems": top, "vertex_centre": float(c["centres"][iv]),
                  "reach_1pct": float(reach_1pct), "reach_single_limit": float(reach_limit)}
    return top, iv, float(reach_1pct)


# ---------------------------------------------------------------------------
# AS3 — SHAPE.  The probe search, with the validity columns that make an
#               endpoint exponent mean something.
# ---------------------------------------------------------------------------
def gate_as3(top, e_def, jobs, out):
    print("\n" + "-" * 96)
    print("AS3  SHAPE — which perturbation of this network can rise as f^+2.8 AT ALL?")
    print("-" * 96)
    c = _ctx()

    jobsl = []
    for pos in POSITIONS:
        kw0 = AJ.ladder_kwargs(pos)
        for e in [k for k, v in kw0.items() if v != 0.0]:
            for fr in FRACS:
                jobsl.append((pos, (e,), (fr,)))
    n_single = len(jobsl)
    for pos in POSITIONS:
        kw0 = AJ.ladder_kwargs(pos)
        avail = [t for t in top if kw0.get(t, 0.0) != 0.0]
        for a, b in itertools.combinations(avail, 2):
            for fa in PAIR_FRACS:
                for fb in PAIR_FRACS:
                    jobsl.append((pos, (a, b), (fa, fb)))
    print(f"  {n_single} single-element probes + {len(jobsl) - n_single} pair probes "
          f"= {len(jobsl)} total, over {len(POSITIONS)} ATTACK throws")

    res = [r for r in parallel.pmap_cpu(probe, jobsl, jobs=jobs) if r is not None]
    print(f"  {len(res)} evaluated (probes whose tilt change is identically zero somewhere on the "
          f"limb are dropped — an endpoint ratio is undefined there)")

    def _fmt(r):
        return (f"  {r['position']:>5s} {'+'.join(r['elems']):>16s} "
                f"{'x'.join(f'{x:g}' for x in r['fracs']):>16s} "
                f"{r['exponent']:+8.3f} {100 * r['reach']:11.3f}% {str(r['sign_ok']):>6s} "
                f"{r['one_signed']:>3d}/{r['n']:<3d} {r['rising']:>3d}/{r['n_step']:<3d}")

    hdr = (f"  {'throw':>5s} {'element(s)':>16s} {'size':>16s} {'exponent':>8s} {'reach':>12s} "
           f"{'sign':>6s} {'1-sgn':>7s} {'rising':>7s}")

    # ---- the trap, printed FIRST because it is what the first draft published ---------------
    naive = sorted(res, key=lambda r: -r["exponent"])[:5]
    print(f"\n  ⚠⚠ READ ON THE ENDPOINT EXPONENT ALONE — this is the table that would have been "
          f"published:")
    print(hdr)
    for r in naive:
        print(_fmt(r))
    bad = [r for r in naive if not clean_shape(r)]
    print(f"\n     {len(bad)} of the top 5 FAIL a validity column — a tilt change that crosses zero "
          f"inside the limb, or")
    print(f"     that turns over inside it, has an endpoint ratio that is an artefact of the "
          f"crossing (AL3's own guard,")
    print(f"     never before pointed at a MECHANISM).  Everything below uses the validated set.")

    clean = [r for r in res if clean_shape(r)]
    sign_ok = [r for r in clean if r["sign_ok"]]
    print(f"\n  validated set: {len(clean)}/{len(res)} probes are single-signed AND monotone rising "
          f"across the limb;")
    print(f"  {len(sign_ok)} of those also carry the deficit's SIGN at the vertex.")

    print(f"\n  TOP 6 BY EXPONENT (validated, sign-admissible):")
    print(hdr)
    for r in sorted(sign_ok, key=lambda r: -r["exponent"])[:6]:
        print(_fmt(r))
    print(f"\n  TOP 6 BY REACH (validated, sign-admissible):")
    print(hdr)
    for r in sorted(sign_ok, key=lambda r: -r["reach"])[:6]:
        print(_fmt(r))

    # ---- the joint frontier ------------------------------------------------------------------
    # ⭐⭐ THREE axes, not two.  The first draft graded exponent against reach and reported "a joint
    # point EXISTS" — true, and the joint points ask for R14 x0.001 (22k -> 22 ohm) and C5 x0.1.
    # Those are not drifts, they are different circuits, and a drive-dependent mechanism can only
    # move an element by a bounded fraction.  The DRIFT ceiling is therefore a graded axis and not
    # a footnote: it is the axis on which this class is actually decided.
    bars = ((SINGLE_POLE_EXPONENT_BOUND, "gate 5's single-pole bound"),
            (AL4_WEAKEST_EXPONENT, "AL4 weakest half-width (most generous)"),
            (e_def, "AL4 primary endpoint (the measurement)"))
    ceilings = ((1.0 + VCO_FILM, "film cap voltage coefficient, 0.1 %"),
                (1.0 + R_TEMPCO, "metal-film resistor self-heating, 1 %"),
                (1.0 + VCO_X7R, "X7R ceramic, 50 % — deliberately generous"),
                (2.0, "a 2x element change — past ANY drift"),
                (10.0, "a 10x element change"),
                (float("inf"), "unbounded — a different circuit"))
    print(f"\n  ⭐ THE JOINT FRONTIER — a carrier needs THREE things at once, and they are in "
          f"tension.")
    print(f"     Cell = max REACH (% of AH7's budget) over validated, sign-admissible probes "
          f"meeting both bars.")
    print(f"\n  {'max element FOLD change':>48s} " + " ".join(f"{'exp>=' + f'{b:.2f}':>14s}"
                                                            for b, _ in bars))
    frontier = {}
    for cap, clab in ceilings:
        cells = []
        for bar, blab in bars:
            okset = [r for r in sign_ok if r["exponent"] >= bar and r["drift"] <= cap]
            best = max(okset, key=lambda r: r["reach"]) if okset else None
            frontier[f"{cap:g}|{bar:.4f}"] = {
                "drift_label": clab, "bar_label": blab, "n": len(okset),
                "max_reach": float(best["reach"]) if best else 0.0,
                "best": {k: best[k] for k in ("position", "elems", "fracs", "exponent",
                                              "reach", "drift")} if best else None}
            cells.append(f"{100 * best['reach']:13.3f}%" if best else f"{'none':>14s}")
        tag = ("unbounded" if math.isinf(cap) else f"<= {cap:g}x")
        print(f"  {tag + '  (' + clab + ')':>48s} " + " ".join(cells))

    best_exp = max(sign_ok, key=lambda r: r["exponent"]) if sign_ok else None
    best_reach = max(sign_ok, key=lambda r: r["reach"]) if sign_ok else None
    if best_exp is None:
        _die("AS3 — no probe survived the validity columns with the right sign; the frontier "
             "cannot be read and this gate will not report one from the unvalidated set.")
    # The physically-bounded arm, read at the most generous of the three ceilings that any real
    # drive-dependent mechanism could supply.
    phys = [r for r in sign_ok if r["drift"] <= 1.0 + VCO_X7R]
    best_phys = max(phys, key=lambda r: r["exponent"]) if phys else None
    # ⭐ AND THE CLEANEST FORM OF THE SAME FACT, WITH NO BAR IN IT AT ALL: how many physically
    # bounded probes even RISE across the limb?  The deficit does, 9/9; a carrier that falls is
    # strongest where the deficit is weakest (AN3's "wrong side of zero").
    phys_all = [r for r in res if r["drift"] <= 1.0 + VCO_X7R]
    phys_rising = [r for r in phys_all if r["rising"] == r["n_step"]]
    print(f"\n  ⭐ THRESHOLD-FREE FORM OF THE SAME RESULT: of the {len(phys_all)} probes at a fold "
          f"change <= {1.0 + VCO_X7R:g}x,")
    print(f"     {len(phys_rising)} have a tilt change that RISES monotonically across the limb — "
          f"the deficit's own shape, 9/9.")
    print(f"     A mechanism that FALLS where the deficit RISES is strongest where the deficit is "
          f"weakest, which needs")
    print(f"     no exponent bar to read (AN3's own wording), and AS4 below shows it is what EVERY small "
          f"perturbation")
    print(f"     of this ladder does.")
    print(f"\n  MAX EXPONENT anywhere in the validated, sign-admissible set : "
          f"{best_exp['exponent']:+.4f}   ({best_exp['position']}/"
          f"{'+'.join(best_exp['elems'])} x{'x'.join(f'{x:g}' for x in best_exp['fracs'])}, "
          f"fold {best_exp['drift']:.0f}x)   deficit {e_def:+.4f}")
    print(f"  MAX REACH    anywhere in the validated, sign-admissible set : "
          f"{100 * best_reach['reach']:.3f}%   (exponent {best_reach['exponent']:+.3f}, "
          f"fold {best_reach['drift']:.0f}x)")
    if best_phys is not None:
        print(f"  MAX EXPONENT at a PHYSICAL drift (fold <= {1 + VCO_X7R:g}x)             : "
              f"{best_phys['exponent']:+.4f}   ({best_phys['position']}/"
              f"{'+'.join(best_phys['elems'])} x"
              f"{'x'.join(f'{x:g}' for x in best_phys['fracs'])}, reach "
              f"{100 * best_phys['reach']:.1f}%)")

    # The best joint probe, per centre, against the deficit — because an endpoint exponent and a
    # monotonicity count are two numbers and the shape is ten.
    key = f"inf|{e_def:.4f}"
    bj = frontier[key]["best"]
    if bj is not None:
        cand = next(r for r in sign_ok
                    if r["position"] == bj["position"] and r["elems"] == bj["elems"]
                    and r["fracs"] == bj["fracs"])
        sc = float(np.dot(cand["shape"], c["deficits"]) / np.dot(cand["shape"], cand["shape"]))
        resid = np.array(cand["shape"]) * sc - c["deficits"]
        rel = float(np.linalg.norm(resid) / np.linalg.norm(c["deficits"]))
        print(f"\n  the BEST UNBOUNDED joint probe, per centre, best-scaled onto the deficit "
              f"(scale {sc:.4g}):")
        print(f"  {'f (Hz)':>9s} {'deficit':>10s} {'mechanism':>11s} {'scaled':>10s} "
              f"{'residual':>10s}")
        for f, dd, mm in zip(c["centres"], c["deficits"], cand["shape"]):
            print(f"  {f:9.1f} {dd:+10.4f} {mm:+11.5f} {mm * sc:+10.4f} {mm * sc - dd:+10.4f}")
        print(f"  ⇒ relative shape residual after best scaling : {rel:.4f} "
              f"({100 * rel:.1f} % of the deficit's own norm)")
        frontier[key]["shape_residual_rel"] = rel
        frontier[key]["shape_scale"] = sc

    out["as3"] = {"n_probes": len(jobsl), "n_evaluated": len(res), "n_single": n_single,
                  "n_clean": len(clean), "n_sign_ok": len(sign_ok),
                  "naive_top": naive, "naive_invalid": len(bad),
                  "top_by_exponent": sorted(sign_ok, key=lambda r: -r["exponent"])[:12],
                  "top_by_reach": sorted(sign_ok, key=lambda r: -r["reach"])[:12],
                  "frontier": frontier, "ceilings": [c_ for c_, _ in ceilings],
                  "best_physical": best_phys,
                  "n_phys_probes": len(phys_all), "n_phys_rising": len(phys_rising),
                  "phys_fold_ceiling": 1.0 + VCO_X7R,
                  "max_exponent": best_exp["exponent"], "max_reach": best_reach["reach"],
                  "max_exponent_drift": best_exp["drift"]}
    return frontier, best_exp, best_reach, best_phys


# ---------------------------------------------------------------------------
# AS4 — the LINEARISED SPAN.  What a finite probe grid cannot say.
# ---------------------------------------------------------------------------
def gate_as4(e_def, out):
    print("\n" + "-" * 96)
    print("AS4  THE REACHABLE SHAPE SET — combinations cannot help either, and here is why")
    print("-" * 96)
    c = _ctx()
    kw0 = AJ.ladder_kwargs("flat")
    elems = [k for k, v in kw0.items() if v != 0.0]
    eps = 1.0e-3
    cols = []
    for e in elems:
        kwp = dict(kw0)
        kwp[e] = kw0[e] * (1.0 + eps)
        cols.append((tilts(kwp, "flat") - c["base"]["flat"]) / eps)
    B = np.array(cols).T                       # (n_centres, n_elements) Jacobian d(tilt)/d ln e

    # The Jacobian is a KNOWN ANSWER against a finite difference of a COMBINED perturbation: if the
    # basis is right, a small mixed drift is reproduced by B @ delta.  Two-sided — it fails if a
    # column is mis-ordered or a sign is dropped.
    rng = np.random.default_rng(20260805)
    dv = rng.normal(scale=1.0e-3, size=len(elems))
    kwm = dict(kw0)
    for e, v in zip(elems, dv):
        kwm[e] = kw0[e] * math.exp(v)
    meas = tilts(kwm, "flat") - c["base"]["flat"]
    pred = B @ dv
    jac_err = float(np.max(np.abs(meas - pred)) / max(np.max(np.abs(meas)), 1e-300))
    print(f"  Jacobian known answer (mixed small drift, measured vs B@d) : {jac_err:.3e} relative")
    if jac_err > 1e-2:
        _die(f"AS4 — the linearised basis does not reproduce a finite-difference combined "
             f"perturbation ({jac_err:.3e} relative); the span argument below rests on it.")

    u, sv, vt = np.linalg.svd(B, full_matrices=False)
    print(f"\n  SVD of the {B.shape[0]}x{B.shape[1]} Jacobian — the SHAPES this ladder can make:")
    print(f"  {'mode':>5s} {'sigma':>13s} {'sigma/sigma1':>13s} {'endpoint exp':>13s}")
    modes = []
    for k in range(len(sv)):
        e_mode = endpoint_exponent(c["centres"], u[:, k])
        modes.append({"sigma": float(sv[k]), "rel": float(sv[k] / sv[0]), "exponent": e_mode})
        if k < 5:
            print(f"  {k + 1:>5d} {sv[k]:13.5e} {sv[k] / sv[0]:13.3e} {e_mode:+13.4f}")
    rank95 = int(np.searchsorted(np.cumsum(sv ** 2) / np.sum(sv ** 2), 0.99) + 1)
    print(f"\n  ⭐ sigma2/sigma1 = {sv[1] / sv[0]:.3e},  sigma3/sigma1 = {sv[2] / sv[0]:.3e}  ⇒ the "
          f"reachable set of tilt-change")
    print(f"     SHAPES is effectively {rank95}-dimensional: to {100 * (1 - (sv[1] / sv[0]) ** 2):.4f} % "
          f"of its energy, EVERY small perturbation of")
    print(f"     this ladder — any element, any combination — makes the SAME curve up to scale, and "
          f"that curve's")
    print(f"     endpoint exponent is {modes[0]['exponent']:+.4f} against the deficit's "
          f"{e_def:+.4f}.")
    print(f"\n  ⚠ SCOPE: this is a statement about SMALL perturbations (a Jacobian).  The large "
          f"ones are AS3's")
    print(f"    business, and they are where the >2 exponents live — at reaches AS3 grades.")
    out["as4"] = {"jacobian_rel_err": jac_err, "modes": modes, "rank99": rank95,
                  "sigma_ratio_2": float(sv[1] / sv[0]), "sigma_ratio_3": float(sv[2] / sv[0]),
                  "mode1_exponent": modes[0]["exponent"], "elements": elems}
    return modes


# ---------------------------------------------------------------------------
# AS5 — ROOT CAUSE, and the positive specification it implies
# ---------------------------------------------------------------------------
def gate_as5(out):
    print("\n" + "-" * 96)
    print("AS5  ROOT CAUSE — the ladder is SPENT at the vertex")
    print("-" * 96)
    c = _ctx()
    zin = AJ.ladder_zin(AI.FINE, position="flat")
    lf = np.log(np.asarray(AI.FINE))
    slope = np.gradient(np.log(np.abs(zin)), lf) * 6.0206      # dB/oct
    print(f"  {'f (Hz)':>9s} {'|Zin|':>11s} {'d ln|Zin| / d ln f':>20s}")
    prof = []
    for target in (100.0, 200.0, 500.0, 1000.0, c["centres"][0], c["f0"], c["centres"][-1],
                   10000.0, 20000.0):
        i = int(np.argmin(np.abs(np.asarray(AI.FINE) - target)))
        prof.append({"f": float(AI.FINE[i]), "zin_k": float(abs(zin[i]) / 1e3),
                     "slope_db_oct": float(slope[i])})
        print(f"  {AI.FINE[i]:9.1f} {abs(zin[i]) / 1e3:10.3f}k {slope[i]:+19.3f} dB/oct")
    i_v = int(np.argmin(np.abs(np.asarray(AI.FINE) - c["f0"])))
    print(f"\n  ⭐⭐ At the vertex |Zin| is falling at only {slope[i_v]:+.3f} dB/oct and by 10 kHz at "
          f"{slope[int(np.argmin(np.abs(np.asarray(AI.FINE) - 1e4)))]:+.3f} — the ladder's caps are")
    print(f"     already near-shorts there, so Zin is asymptotically CONSTANT.  A perturbation of a")
    print(f"     frequency-flat impedance changes the drain transfer by a pure GAIN, and a gain has")
    print(f"     ZERO tilt.  That is why every mode in AS4 FALLS: the mechanism is spent before it")
    print(f"     reaches the band the deficit lives in.")
    print(f"\n  ⇒ AK's root cause in a THIRD guise (its shelf corners at 219/292 Hz, a decade below")
    print(f"    the vertex; AJ's moving-pole class and AN's ro/rq2 the same) — and item 6's gate 6")
    print(f"    stated positively: a viable carrier needs STRUCTURE AT OR ABOVE ~2.9 kHz.  This")
    print(f"    ladder has none, by measurement, whatever element you move.")
    out["as5"] = {"profile": prof, "slope_at_vertex": float(slope[i_v])}
    return float(slope[i_v])


# ---------------------------------------------------------------------------
# AS6 — the ADDED-element branch (a perturbation need not be a drift)
# ---------------------------------------------------------------------------
def gate_as6(e_def, out):
    print("\n" + "-" * 96)
    print("AS6  ADDED ELEMENT — a perturbation of a network need not be a drift of one of its parts")
    print("-" * 96)
    c = _ctx()
    print(f"  The shipped `trebleC8` is ZERO (s99/s100 took C8 out of circuit), so C8 is not a")
    print(f"  drift in AS3's sense — it is an element APPEARING, and the ATTACK switch gives it two")
    print(f"  different topologies for free: a shunt at node P ('cut') and a bridge across R8")
    print(f"  ('boost').  Swept over eight decades, which is any stray, junction or coupling")
    print(f"  capacitance that could plausibly appear anywhere in this network.")
    rows = []
    print(f"\n  {'throw':>6s} {'C8':>10s} {'dT @vertex':>12s} {'reach':>10s} {'exponent':>9s} "
          f"{'1-sgn':>7s} {'rising':>7s}")
    iv = int(np.argmin(np.abs(c["centres"] - c["f0"])))
    for pos in ("cut", "boost"):
        kw0 = AJ.ladder_kwargs(pos)
        base = c["base"][pos]
        for cap in (1e-13, 1e-12, 1e-11, 1e-10, 1e-9, 1e-8, 1e-7, 1e-6):
            kw = dict(kw0)
            kw["C8"] = cap
            d = tilts(kw, pos) - base
            if not np.all(np.isfinite(d)) or np.abs(d).min() <= 0.0:
                continue
            col = shape_columns(d)
            r = {"position": pos, "C8": cap, "d_vertex": float(d[iv]),
                 "reach": float(abs(d[iv] / c["budget"])), **col,
                 "sign_ok": bool((d[iv] < 0.0) == (c["budget"] < 0.0))}
            rows.append(r)
            print(f"  {pos:>6s} {cap:10.1e} {d[iv]:+12.6f} {100 * r['reach']:9.3f}% "
                  f"{col['exponent']:+9.3f} {col['one_signed']:>3d}/{col['n']:<3d} "
                  f"{col['rising']:>3d}/{col['n_step']:<3d}")
    valid = [r for r in rows if clean_shape(r) and r["sign_ok"]]
    best = max(valid, key=lambda r: r["exponent"]) if valid else None
    e_added = best["exponent"] if best else float("-inf")
    print(f"\n  best VALIDATED, sign-admissible added-element exponent : "
          + (f"{e_added:+.4f}" if best else "none survives the validity columns"))
    print(f"\n  ⭐ And the two branches close ANALYTICALLY, so the sweep is a check rather than the")
    print(f"    argument.  For any passive RC block added to this network:")
    print(f"      * its corners BELOW the band  ⇒ it is asymptotically a constant there, so its")
    print(f"        contribution to the tilt CHANGE decays — AS5's mechanism, exponent < 0;")
    print(f"      * its corners ABOVE the band  ⇒ log|H| = c0 + c1 f^2 + O(f^4), so the tilt change")
    print(f"        is proportional to f^2 and the endpoint exponent approaches 2 FROM BELOW — which")
    print(f"        is gate 5's bound, and AS1e measures the estimator returning exactly it.")
    print(f"    Either way an added element is bounded by 2.000 against the deficit's {e_def:+.4f}.")
    out["as6"] = {"rows": rows, "best_exponent": (e_added if best else None),
                  "n_valid": len(valid)}
    return e_added


# ---------------------------------------------------------------------------
# AS7 — gate 4, the GRUNT-sign consistency screen
# ---------------------------------------------------------------------------
def gate_as7(out):
    print("\n" + "-" * 96)
    print("AS7  GATE 4 — GRUNT-sign consistency (free, threshold-free)")
    print("-" * 96)
    c = _ctx()
    print(f"  The treble ladder sits UPSTREAM of the GRUNT switch and the tilt operator is linear")
    print(f"  on log-magnitude, so the GRUNT bank contributes the same slope at both ends of the")
    print(f"  drive ladder and cancels EXACTLY from the tilt CHANGE.  Asserted, not argued:")
    kw0 = AJ.ladder_kwargs("flat")
    kwp = dict(kw0)
    kwp["C5"] = kw0["C5"] * 0.5
    base = c["base"]["flat"]
    dmech = tilts(kwp, "flat") - base
    caps = AI.grunt_caps()
    spread = []
    for name, cg in caps.items():
        gdb = 20.0 * np.log10(np.abs(AI.h_at(AI.FINE, AB.CLIP_A0, cg)) + 1e-300)
        t_b = np.array([AI.tilt_fine(
            AK.drain_db(c["gm"], c["ro"], c["rq2"],
                        AJ.ladder_zin(AI.FINE, position="flat", which=kw0)) + gdb, f, c["half"])
            for f in c["centres"]])
        t_p = np.array([AI.tilt_fine(
            AK.drain_db(c["gm"], c["ro"], c["rq2"],
                        AJ.ladder_zin(AI.FINE, position="flat", which=kwp)) + gdb, f, c["half"])
            for f in c["centres"]])
        spread.append(np.max(np.abs((t_p - t_b) - dmech)))
        print(f"    GRUNT {name:>5s} (Cg {cg * 1e9:7.3f} nF): worst departure from the "
              f"GRUNT-free tilt change {spread[-1]:.3e} dB/oct")
    worst = float(max(spread))
    passes = worst < 1e-9
    print(f"\n  ⇒ the candidate is GRUNT-INDEPENDENT to {worst:.2e} dB/oct, so it passes gate 4 at "
          f"3 of 3 positions.")
    print(f"  ⚠⚠ AND IT IS STILL REFUTED (AS8).  GATE AK made exactly this point with the J201's")
    print(f"     shaper: SIGN-ADMISSIBILITY IS NECESSARY, NOT SUFFICIENT — a screen built on the")
    print(f"     GRUNT sign alone would have passed this class too.")
    out["as7"] = {"worst_departure": worst, "passes": bool(passes),
                  "caps": {k: float(v) for k, v in caps.items()}}
    return bool(passes)


# ---------------------------------------------------------------------------
# AS8 — VERDICT (computed, never narrated)
# ---------------------------------------------------------------------------
def gate_as8(e_def, frontier, best_exp, best_reach, best_phys, modes, slope_v, e_added,
             grunt_ok, reach_1pct, out):
    print("\n" + "=" * 96)
    print("AS8  VERDICT  (computed from AS2–AS7, never narrated)")
    print("=" * 96)
    gen = frontier[f"inf|{AL4_WEAKEST_EXPONENT:.4f}"]
    meas = frontier[f"inf|{e_def:.4f}"]
    gen_phys = frontier[f"{1.0 + VCO_X7R:g}|{AL4_WEAKEST_EXPONENT:.4f}"]

    size_is_free = best_reach["reach"] >= 1.0
    shape_reaches = best_exp["exponent"] >= AL4_WEAKEST_EXPONENT
    joint = gen["max_reach"] >= 1.0                       # unbounded drift
    joint_physical = gen_phys["max_reach"] >= 1.0         # drift a mechanism could supply

    lines = []
    if size_is_free:
        lines.append(
            f"⭐⭐ THE LEVER IS REAL AT A LIMIT — AND THAT MAKES THIS THE FIRST PRE-CLIPPER CLASS "
            f"NOT REFUTED ON SIZE.  A validated, sign-admissible ladder perturbation reaches "
            f"{100 * best_reach['reach']:.0f} % of AH7's budget, against AK's 2.46 %, AJ's 0.17 % "
            f"and AN's 1.33 % at THEIR limits.  AO4's specification was right about the lever. "
            f"⚠⚠ BUT QUOTE THE SECOND NUMBER WITH IT: at a 1 % drift of the best element the reach "
            f"is {100 * reach_1pct:.4f} %, i.e. the geometric lever is real and a PHYSICAL drift "
            f"still lands in the same order as the classes already refuted.")
    else:
        lines.append(
            f"⛔ REFUTED ON SIZE — the largest validated, sign-admissible reach anywhere in the "
            f"probe set is {100 * best_reach['reach']:.3f} % of AH7's budget.")

    if shape_reaches:
        lines.append(
            f"⚠ AND THE CLASS IS NOT SHAPE-REFUTED THE WAY ITS PREDECESSORS WERE: a multi-element "
            f"perturbation moves every pole and zero at once, so gate 5's `<= 2` single-pole bound "
            f"does NOT apply to it, and the validated set does contain exponents up to "
            f"{best_exp['exponent']:+.3f}.  Do not quote gate 5 against this class.")
    else:
        lines.append(
            f"⛔⛔ REFUTED ON SHAPE, AND ON A BOUND THAT WAS NOT AVAILABLE A PRIORI: the largest "
            f"endpoint exponent anywhere in the validated, sign-admissible probe set is "
            f"{best_exp['exponent']:+.4f}, against the deficit's {e_def:+.4f} (weakest half-width "
            f"{AL4_WEAKEST_EXPONENT:.3f}).  Gate 5's single-pole bound does not cover a "
            f"multi-element perturbation — this had to be measured, and it comes out under the "
            f"bound anyway.")

    if joint and not joint_physical:
        bj = gen["best"]
        lines.append(
            f"⛔⛔ AND THE CLASS IS DECIDED ON A THIRD AXIS ENTIRELY — THE SIZE OF THE ELEMENT "
            f"CHANGE.  A joint point (exponent AND reach) does exist, and it asks for "
            f"{bj['position']}/{'+'.join(bj['elems'])} at "
            f"x{'x'.join(f'{x:g}' for x in bj['fracs'])} — a "
            f"{bj['drift']:.0f}x element change, i.e. a DIFFERENT CIRCUIT rather than a "
            f"drift.  Held to a drift a drive-dependent mechanism could actually supply "
            f"(fold <= {1 + VCO_X7R:g}x, X7R ceramic and deliberately generous — film is 0.1 %, a "
            f"resistor's self-heating ~1 %), {gen_phys['n']} of {out['as3']['n_sign_ok']} "
            f"validated sign-admissible probes clear the most generous exponent bar and the best "
            f"reaches {100 * gen_phys['max_reach']:.3f} %"
            + (f"; the steepest physically-bounded probe anywhere reads "
               f"{best_phys['exponent']:+.3f}."
               if best_phys else
               f" — and threshold-free, of the {out['as3']['n_phys_probes']} probes at that fold "
               f"ceiling, {out['as3']['n_phys_rising']} have a tilt change that even RISES across "
               f"the limb, against the deficit's 9/9.")
            + f"  ⇒ steepness on this network is bought by CANCELLATION between two large "
              f"element moves, and the cancellation is what needs the moves to be large.")
    elif joint_physical:
        lines.append(
            f"⚠⚠ A PHYSICALLY-BOUNDED JOINT POINT EXISTS — {gen_phys['n']} probes clear the most "
            f"generous exponent bar at a fold change of <= {1 + VCO_X7R:g}x AND one of them reaches "
            f"{100 * gen_phys['max_reach']:.1f} %.  This class is NOT refuted; read AS3's frontier "
            f"before doing anything else.")
    else:
        lines.append(
            f"⛔⛔ THE REQUIREMENTS ARE NOT SATISFIABLE TOGETHER, WHICH IS THE ACTUAL RESULT.  "
            f"At the most generous exponent bar ({AL4_WEAKEST_EXPONENT:.3f}, AL4's weakest "
            f"half-width) {gen['n']} of {out['as3']['n_sign_ok']} validated sign-admissible probes "
            f"clear it, and the best of them reaches {100 * gen['max_reach']:.3f} % of the budget; "
            f"at the measured exponent ({e_def:.3f}) it is {meas['n']} probes and "
            f"{100 * meas['max_reach']:.3f} %.  Meanwhile the probes that REACH "
            f"({100 * best_reach['reach']:.0f} %) carry exponent {best_reach['exponent']:+.3f}.")

    lines.append(
        f"⭐ WHY, AND IT GENERALISES: |Zin| falls at only {slope_v:+.3f} dB/oct at the vertex and is "
        f"asymptotically CONSTANT above it, so a perturbation of it is a pure GAIN change there — "
        f"which has zero tilt.  AS4 measures the consequence directly: sigma2/sigma1 = "
        f"{out['as4']['sigma_ratio_2']:.2e}, so to {100 * (1 - out['as4']['sigma_ratio_2'] ** 2):.4f} % "
        f"of its energy EVERY small perturbation of this ladder makes ONE shape, whose exponent is "
        f"{modes[0]['exponent']:+.3f}.  This is AK's root cause (corners a decade below the vertex) "
        f"in a third guise, and item 6's gate 6 stated positively.")

    if e_added > AL4_WEAKEST_EXPONENT:
        lines.append(f"⚠ THE ADDED-ELEMENT BRANCH REACHES ON SHAPE ({e_added:+.3f}) — read AS6.")
    else:
        lines.append(
            f"⛔ THE ADDED-ELEMENT BRANCH FALLS TOO — best validated exponent "
            + (f"{e_added:+.3f}" if math.isfinite(e_added) else "none valid")
            + f", and it closes analytically either way: an added RC block cornering BELOW the band "
              f"is spent there, and one cornering ABOVE it has log|H| = c0 + c1 f^2, i.e. exponent "
              f"-> 2 from below, which is gate 5.")

    if grunt_ok:
        lines.append(
            f"⭐⭐ AND THE METHODOLOGICAL RESULT, FOR THE SECOND TIME: this carrier PASSES item 6's "
            f"GRUNT-sign gate at 3 of 3 positions (it is upstream of the switch, asserted to "
            f"{out['as7']['worst_departure']:.1e}) and is still refuted.  AK said it of the J201's "
            f"shaper; a screen built on sign alone would have passed this class too.")
    else:
        lines.append(
            f"⛔ THE CANDIDATE IS GRUNT-DEPENDENT — its tilt change departs from the GRUNT-free one "
            f"by {out['as7']['worst_departure']:.2e} dB/oct, so it fails item 6's gate 4 the way "
            f"the clipper's own `a0` sag did (AI, right sign at 1 of 3 positions).  That is a "
            f"refutation in its own right and does not need any of the above.")

    for ln in lines:
        print(f"\n  {ln}")

    print(f"\n  ⚠ WHAT THIS GATE DOES **NOT** CLAIM:")
    print(f"    * AS3's frontier is a SEARCH over {out['as3']['n_probes']} probes, not a theorem — "
          f"AS4 covers the")
    print(f"      small-perturbation directions a finite grid cannot enumerate, and AS6 covers "
          f"added elements,")
    print(f"      but a large, many-element, finely-tuned drift outside the grid is not excluded "
          f"by measurement.")
    print(f"    * it screens the REACHABLE SET; it names no physical carrier for a drive-dependent "
          f"ladder Zin,")
    print(f"      and AO4's own candidate list for one was thin.")
    print(f"    * nothing is graded against hardware, nothing renders, no constant moves, no "
          f"baseline is touched.")

    out["as8"] = {"lines": lines, "size_is_free": bool(size_is_free),
                  "shape_reaches": bool(shape_reaches), "joint": bool(joint),
                  "joint_physical": bool(joint_physical),
                  "max_exponent": best_exp["exponent"], "max_reach": best_reach["reach"],
                  "frontier_generous": gen, "frontier_measured": meas,
                  "frontier_generous_physical": gen_phys}
    return size_is_free, shape_reaches, joint, joint_physical


# ---------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ag", default=AG_REPORT)
    ap.add_argument("--ah", default=AH_REPORT)
    ap.add_argument("--al", default=AL_REPORT)
    ap.add_argument("--out", default=OUT_JSON)
    parallel.add_jobs_arg(ap)
    a = ap.parse_args()

    root = os.path.dirname(HERE)
    for p in (a.ag, a.ah, a.al):
        if not os.path.exists(os.path.join(root, p)):
            _die(f"stored report {p} not found — this gate imports its target rather than "
                 f"transcribing it, and will not invent one.")

    c = _ctx()
    print("=" * 96)
    print("GATE AS — a DRIVE-DEPENDENT TREBLE-LADDER `Zin` as item 6's tilt carrier")
    print("=" * 96)
    print(f"  vertex f0 {c['f0']:.1f} Hz   half-window {c['half']:.6f} oct   "
          f"budget {c['budget']:+.4f} dB/oct (AH7)")
    print(f"  limb {c['centres'][0]:.1f} -> {c['centres'][-1]:.1f} Hz, {len(c['centres'])} centres "
          f"(AL4's own, imported)")
    print(f"\n  ⚠⚠ WHY THIS GATE EXISTS: `zin` is the ONE parameter GATE AK's own mechanism function")
    print(f"     accepts and never moved (AO2 classifies it KA-ONLY), and by AO1c's exact identity")
    print(f"     the LOAD side of the drain-node divider carries ~5x the lever of the SOURCE side —")
    print(f"     where every carrier screened so far acts.  AO established the lever and did not")
    print(f"     screen it; this gate screens it, starting from AO's own shape question.")

    out = {"report_ag": a.ag, "report_ah": a.ah, "report_al": a.al,
           "f0": c["f0"], "half_oct": c["half"], "budget": c["budget"],
           "ladder_vals": AJ.LADDER_VALS,
           "centres": [float(x) for x in c["centres"]],
           "deficits": [float(x) for x in c["deficits"]]}

    e_def, _ = gate_as1(out)
    top, _, reach_1pct = gate_as2(out)
    frontier, best_exp, best_reach, best_phys = gate_as3(top, e_def, a.jobs, out)
    modes = gate_as4(e_def, out)
    slope_v = gate_as5(out)
    e_added = gate_as6(e_def, out)
    grunt_ok = gate_as7(out)
    size_free, shape_reaches, joint, joint_phys = gate_as8(
        e_def, frontier, best_exp, best_reach, best_phys, modes, slope_v, e_added, grunt_ok,
        reach_1pct, out)

    os.makedirs(os.path.join(root, os.path.dirname(a.out)), exist_ok=True)
    json.dump(out, open(os.path.join(root, a.out), "w"), indent=1)
    print(f"\nwrote {a.out}")

    # A computed verdict, never a narrated one.  This gate EXITS 0 whatever the physics says —
    # the outcome is a property of the device, not of the instrument (s108).
    print(f"\nAS-MEMBERSHIP size_is_free={size_free} shape_reaches={shape_reaches} joint={joint} "
          f"joint_physical={joint_phys} max_exp={best_exp['exponent']:.4f} "
          f"max_reach={best_reach['reach']:.6f} e_def={e_def:.4f} grunt_ok={grunt_ok} "
          f"added_exp={e_added:.4f} "
          f"phys_exp={best_phys['exponent'] if best_phys else float('nan'):.4f}")


if __name__ == "__main__":
    main()
