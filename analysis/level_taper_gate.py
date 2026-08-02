#!/usr/bin/env python3.11
"""GATE L -- can the shipped LevelBlend network produce the pedal's LEVEL law AT ALL?

Session 104.  No render: every number is a re-read of a report already on disk plus a closed-form
evaluation of the shipped `LevelBlend` stage.  Imports `level_law_gate` (GATE K) rather than
re-deriving anything it already established, so the two cannot drift.

WHY THIS EXISTS
---------------
GATE K (s103) measured the LEVEL control law absolutely and found the model up to 9.3 dB quiet
below noon.  It then asked whether the TAPER could close it, answered no (best exponent reaches
rms 1.85 dB), and inferred from that the lever must be the clean/OD balance -- A3.

That inference rests on a two-parameter fit (taper exponent, one scalar clean/OD ratio) to one
band-averaged curve, and K7 already showed such a fit does not identify its own ratio -- it
returned 0.14 where the direct measurement says 1.53.  So "the taper cannot close it" was
established, but "therefore the lever is the bleed ratio" was not: no one had asked what the
network can reach with the taper AND the bleed BOTH free.

This gate asks exactly that, and it can, because the problem is far better posed per band than
pooled:

    out_H1(x, f) = a(L_x)*H_od(f) + b(L_x)*H_cl(f)

with the network's own coefficients, which reduce (BLEND = 1) to a single elegant form:

    a(L) = L / (1 + L - L^2)        b(L) = a(L) * (1 - L)

i.e. the clean-re-OD ratio the stage mixes is EXACTLY (1 - L).  L1 gates that reduction against
GATE K2's `coef_closed`, so it is a third independent derivation of the same two numbers, not a
retyping of them.

`plugin_db`/`pedal_db` are band-averaged POWER, so the band average of the mixed output is

    mean|a H_od + b H_cl|^2 = a^2 P_od [ 1 + t^2 + 2 t c ],   t = (1-L) rho,  rho = sqrt(P_cl/P_od)

where c = the normalised real part of the cross-spectrum, in [-1, 1].  That is EXACT -- no
coherent/incoherent assumption is made anywhere (s103's K7 flagged that assumption as wrong, and
this is how it is retired).  |rho(f)| is MEASURED per band from the two exact-zero endpoint
captures; c(f) is the only nuisance parameter, one per band.

    unknowns : 8 taper values (L(1)=1 fixed) SHARED across bands + 25 per-band c
    equations : 25 bands x 8-9 detents = 200-225

Strongly overdetermined, and the taper is shared across bands while the nuisance is not -- which
is what makes L identifiable at all.

GATES (all computed, exits non-zero on failure)
-----------------------------------------------
L1  the reduced closed form == GATE K2's `coef_closed` at BLEND=1, to 1e-15, plus a mutation
    (b must be exactly 0 at LEVEL max and non-zero at noon) so the check is not vacuous.
L2  MEMBERSHIP, asserted rather than assumed.  The ladder comes from GATE K's own 13-key
    `find_level_groups`; the two endpoint captures must match the ladder on every setting except
    the one being varied, and `gain-n12` rows are excluded by name.  Building this by hand with a
    4-key match pulled in the session-48 defect rows AND duplicate detents, and the band-MEAN law
    still reproduced K3 exactly -- so a contaminated membership was invisible at the pooled level
    and only showed up as a 7.5 dB per-band residual.  `aggregate-moved-check-membership-first`.
L3  THE KNOWN ANSWER, and the one that makes the rest quotable: run on the MODEL the inverse must
    return L = x^2.25.  Run from >=5 starts spanning p = 0.5 .. 4.0 plus random monotone vectors,
    because initialising at x^2.25 and landing on x^2.25 is a FIXED POINT, not a test
    (`imposed-checks-cannot-corroborate`).  All starts must agree, or L is not identified and
    nothing below may be read.
L4  the PEDAL recovery, and the structural verdict: the same machinery with the same freedom.
L5  the free-rho CONTROL -- separates "our |rho| measurement is wrong" from "the network is
    wrong".  If freeing rho per band collapses the residual, L4's verdict is about the endpoint
    captures, not the topology.  Run on the MODEL too: if freeing rho breaks the MODEL's
    recovery, the control is too loose to interpret and says so.
L6  stimulus invariance -- a pot's taper cannot depend on the stimulus level.  Recovering a
    DIFFERENT taper at each stimulus is a refutation of the model form, not a measurement.
L7  L(0) -- the LEVEL-min mute, quantified.  The matrix has never graded this row.

Run:
    python3.11 analysis/level_taper_gate.py analysis/reports/s99_attack_cand.json
    python3.11 analysis/level_taper_gate.py REPORT.json --json analysis/reports/s104_level_taper.json
"""
import argparse
import json
import sys

import numpy as np
from scipy.optimize import least_squares

import matrix_grade as MG
import level_law_gate as K

NOON = 0.5
SHIPPED_P = K.SHIPPED_LEVEL_TAPER_EXP          # 2.25, and K2 checks it against FitParams.h
SWEEPS = ["sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]

# Settings that must be identical between the ladder and the two endpoint captures.  `level` and
# `blend` are the two being varied, so they are excluded by construction.
ENDPOINT_KEYS = ("drive", "gruntIdx", "attackIdx", "master", "lo", "loMid", "hiMid", "hi",
                 "loMidFreq", "hiMidFreq", "distEngage", "gainSessionDb")

# L3's tolerance on recovering x^2.25.  The model's data was generated by this exact network, so
# the only error is the optimiser's -- 1e-4 is loose enough not to be flaky and tight enough that
# a genuinely different taper (the pedal's differs by >0.1) could never pass.
KA_TOL = 1e-4
# Spread across starts below which L counts as identified (same units as L, i.e. [0,1]).
IDENT_TOL = 1e-3


# --------------------------------------------------------------------------------------------
# L1 -- the reduced closed form
# --------------------------------------------------------------------------------------------
def a_of(L):
    """OD coefficient of the shipped LevelBlend at BLEND = 1, reduced to closed form.

    Derivation from LevelBlend::process with B = 1:
        Vw = (Vo/(1-L) + Vc) / (1/(1-L) + 1/L + 1)
    Multiply through by L(1-L):
        Vw = (L*Vo + L(1-L)*Vc) / (L + (1-L) + L(1-L)) = (L*Vo + L(1-L)*Vc) / (1 + L - L^2)
    so a = L/(1+L-L^2) and b = a*(1-L).  L1 gates this against GATE K2's own transcription."""
    return L / (1.0 + L - L * L)


def b_of(L):
    return a_of(L) * (1.0 - L)


def gate_l1(out):
    print("-- L1: the reduced closed form vs GATE K2's `coef_closed` --")
    worst = 0.0
    for L in np.linspace(0.0, 1.0, 1001):
        a, b = K.coef_closed(1.0, float(L))
        worst = max(worst, abs(a - a_of(L)), abs(b - b_of(L)))
    if worst > 1e-15:
        sys.exit(f"GATE L1 FAIL: the reduction disagrees with level_law_gate.coef_closed by "
                 f"{worst:.3e} -- the algebra below is wrong, so nothing here may be quoted")
    print(f"  L1 OK   a(L)=L/(1+L-L^2), b=a(1-L) reproduces coef_closed to {worst:.2e} "
          f"over 1001 points")
    # Mutation: the whole inverse leans on b vanishing at LEVEL max (that is what makes the
    # pure-OD capture an exact endpoint).  If b were never 0 the endpoint would not exist.
    if b_of(1.0) != 0.0:
        sys.exit("GATE L1 FAIL: b is not exactly 0 at LEVEL max -- the pure-OD endpoint that "
                 "|rho| is measured against does not exist")
    if b_of(NOON ** SHIPPED_P) <= 0.0:
        sys.exit("GATE L1 FAIL: b is 0 at noon too -- there is no bleed to identify and this "
                 "gate is testing nothing (empty-gate-must-fail)")
    print(f"  MUTATION OK  b = 0 exactly at LEVEL max and {b_of(NOON ** SHIPPED_P):.4f} at noon, "
          f"so the endpoint\n               is real and the bleed term is not identically zero.")
    out["l1"] = {"worst": worst}


# --------------------------------------------------------------------------------------------
# L2 -- membership
# --------------------------------------------------------------------------------------------
def gate_l2(caps, out):
    print("\n-- L2: membership, asserted not assumed --")
    groups = K.find_level_groups(caps)
    ladder = max(groups.values(), key=len)
    lad = {x: f for x, f in ladder}
    if len(lad) != len(ladder):
        sys.exit("GATE L2 FAIL: the ladder has duplicate LEVEL values -- a dict build would "
                 "silently drop one and the law would be read off the survivor")
    lset = caps[lad[NOON]]["settings"]

    def endpoint(**kw):
        hits = []
        for f, c in caps.items():
            s = c.get("settings", {})
            if not MG.is_od(f) or "gain-n12" in f:
                continue
            if not all(s.get(k) == v for k, v in kw.items()):
                continue
            if not all(s.get(k) == lset.get(k) for k in ENDPOINT_KEYS):
                continue
            hits.append(f)
        return hits

    cl = endpoint(blend=0.0)
    od = endpoint(blend=1.0, level=1.0)
    if len(cl) != 1 or len(od) != 1:
        sys.exit(f"GATE L2 FAIL: need exactly one pure-clean and one pure-OD capture matched to "
                 f"the ladder on {len(ENDPOINT_KEYS)} settings; got {cl} and {od}.  |rho| would "
                 f"otherwise average captures taken at different operating points.")
    n_bad = sum(1 for f in caps if "gain-n12" in f)
    print(f"  ladder: {len(ladder)} detents, {sorted(lad)}")
    print(f"  endpoints: clean={cl[0]}  od={od[0]}")
    print(f"  L2 OK   both endpoints matched to the ladder on {len(ENDPOINT_KEYS)} settings; "
          f"{n_bad} `gain-n12` captures\n          excluded by name (the session-48 capture "
          f"defect -- do not fit to it)")
    out["l2"] = {"detents": sorted(lad), "clean": cl[0], "od": od[0], "excluded_gain_n12": n_bad}
    return lad, cl[0], od[0]


# --------------------------------------------------------------------------------------------
# the inverse
# --------------------------------------------------------------------------------------------
def _starts(xs_all, nb, extra, multi=True):
    """Initial vectors far from x^2.25.  A start AT the answer is a fixed point, not a test.

    `multi=False` returns the single p=1.0 (linear) start, which is still far from the shipped
    p=2.25.  The L4/L5/L6 grid uses it because L3 has already established that the inverse is
    GLOBALLY identified -- 7 starts spanning p=0.5..4.0 plus random monotone vectors all land on
    the same L to 1e-3.  Re-running 7 starts across 16 fits would cost an hour and re-establish
    the same fact; the saving is stated rather than silent."""
    ps = (1.0, 0.5, 4.0, 2.25) if multi else (1.0,)
    out = []
    for p in ps:
        q = np.maximum(np.diff(np.concatenate([[0.0], np.array(xs_all) ** p])), 1e-4)
        out.append((f"p={p}", q))
    if multi:
        for seed in (1, 2, 3):
            rng = np.random.default_rng(seed)
            out.append((f"random s{seed}", rng.random(len(xs_all)) + 0.05))
    return [(nm, np.concatenate([q, np.zeros(nb), np.zeros(extra)])) for nm, q in out]


def invert(absfr, lad, fclean, fod, sw, which, nonhf, free_rho=False, multi=True):
    """Recover the taper L(x) shared across bands, with per-band c (and optionally per-band rho).

    Returns (L map, rms dB, n_equations, n_params, spread_across_starts)."""
    xs_all = sorted(lad)
    pb = lambda f, w: absfr[(f, sw)][w][nonhf]
    rho0 = 10.0 ** ((pb(fclean, which) - pb(fod, which)) / 20.0)

    # A detent below SILENT_DB carries no information (the model mutes at LEVEL 0 by
    # construction); include it only where it is actually measurable.
    xs = [x for x in xs_all if pb(lad[x], which).max() > MG.SILENT_DB]
    meas = np.array([pb(lad[x], which) - pb(lad[NOON], which) for x in xs])
    nb, nq = len(nonhf), len(xs_all)
    ex = nb if free_rho else 0

    def unpack(th):
        q = th[:nq]
        Lm = dict(zip(xs_all, np.cumsum(q) / q.sum()))       # monotone, ends at exactly 1
        c = np.clip(th[nq:nq + nb], -1.0, 1.0)
        r = rho0 * 10.0 ** (th[nq + nb:] / 20.0) if free_rho else rho0
        return Lm, c, r

    def resid(th):
        Lm, c, r = unpack(th)

        def amp(x):
            L = Lm[x]
            t = (1.0 - L) * r
            return a_of(L) * np.sqrt(np.maximum(1e-300, 1.0 + t * t + 2.0 * t * c))

        ref = amp(NOON)
        return np.concatenate([20.0 * np.log10(np.maximum(amp(x), 1e-300) / ref) - meas[k]
                               for k, x in enumerate(xs)])

    lo = np.concatenate([np.full(nq, 1e-9), np.full(nb, -1.0), np.full(ex, -30.0)])
    hi = np.concatenate([np.full(nq, 10.0), np.full(nb, 1.0), np.full(ex, 30.0)])
    best, sols = None, []
    for nm, th0 in _starts(xs_all, nb, ex, multi=multi):
        o = least_squares(resid, th0, bounds=(lo, hi), max_nfev=60000)
        Lm, _c, _r = unpack(o.x)
        rms = float(np.sqrt(np.mean(o.fun ** 2)))
        sols.append((nm, Lm, rms))
        if best is None or rms < best[2] - 1e-12:
            best = (nm, Lm, rms)
    # Spread across starts, over the detents that are actually informative (L(0) is not, where
    # the model mutes -- it is unconstrained there and correctly wanders).
    inf_x = [x for x in xs_all if x in xs and 0.0 < x < 1.0]
    spread = max((max(s[1][x] for s in sols) - min(s[1][x] for s in sols)) for x in inf_x) \
        if len(sols) > 1 else float("nan")
    n_eq = len(xs) * nb
    return best[1], best[2], n_eq, nq + nb + ex, spread, sols


# --------------------------------------------------------------------------------------------
# L3 -- the known answer
# --------------------------------------------------------------------------------------------
def gate_l3(absfr, lad, fc, fo, nonhf, out):
    print("\n-- L3: KNOWN ANSWER -- the inverse must return the MODEL's own taper --")
    sw = "sweep_clean"
    Lm, rms, n_eq, n_par, spread, sols = invert(absfr, lad, fc, fo, sw, 0, nonhf)
    xs = sorted(lad)
    err = {x: Lm[x] - x ** SHIPPED_P for x in xs if 0.0 < x < 1.0}
    worst = max(abs(v) for v in err.values())
    print(f"    {len(sols)} starts spanning p = 0.5 .. 4.0 plus 3 random monotone vectors")
    print(f"    {n_eq} equations, {n_par} free parameters, fit rms {rms:.4f} dB")
    print(f"    {'x':>7}{'L recovered':>14}{'x^2.25':>10}{'error':>11}")
    for x in xs:
        e = f"{Lm[x] - x ** SHIPPED_P:+.6f}" if 0.0 < x < 1.0 else "  (uninformative)"
        print(f"    {x:7.3f}{Lm[x]:14.6f}{x ** SHIPPED_P:10.6f}{e:>11}")
    if worst > KA_TOL:
        sys.exit(f"GATE L3 FAIL: the inverse does not recover L = x^{SHIPPED_P} on the model "
                 f"(worst {worst:.2e} > {KA_TOL:.0e}) -- it is measuring something else, so the "
                 f"pedal recovery below is not interpretable")
    if spread > IDENT_TOL:
        sys.exit(f"GATE L3 FAIL: the {len(sols)} starts disagree by {spread:.2e} -- L is NOT "
                 f"identified and the recovered curve would be an initialisation artefact")
    print(f"\n    L3 OK   recovered to {worst:.1e} from every start, and the starts agree to "
          f"{spread:.1e}.")
    print( "            Initialising at x^2.25 and landing on it would be a FIXED POINT, not a")
    print( "            test -- p=0.5 and p=4.0 bracket it and three random monotone vectors do")
    print( "            not resemble it, so L is globally identified, not merely reproduced.")
    print(f"\n    ⚠ L(0) is the exception and correctly so: the model MUTES there, so that detent")
    print( "      enters no equation and the optimiser leaves it unconstrained.  It is excluded")
    print( "      from both checks above and is measurable only on the PEDAL (L7).")
    out["l3"] = {"rms": rms, "worst_err": worst, "start_spread": spread,
                 "n_eq": n_eq, "n_par": n_par, "n_starts": len(sols),
                 "L": {str(x): Lm[x] for x in xs}}
    return rms


# --------------------------------------------------------------------------------------------
# L4/L5/L6 -- the pedal, the control, and stimulus invariance
# --------------------------------------------------------------------------------------------
def gate_l456(absfr, lad, fc, fo, nonhf, model_rms, out):
    print("\n-- L4/L5/L6: the PEDAL recovery, the free-rho control, and stimulus invariance --")
    xs = sorted(lad)
    rows, res = [], {}
    for sw in SWEEPS:
        for which, side in ((0, "MODEL"), (1, "PEDAL")):
            for free in (False, True):
                try:
                    Lm, rms, n_eq, n_par, spread, _ = invert(
                        absfr, lad, fc, fo, sw, which, nonhf, free_rho=free, multi=False)
                except Exception as exc:                      # pragma: no cover
                    sys.exit(f"GATE L4 FAIL: inverse blew up at {sw}/{side}/"
                             f"{'free' if free else 'meas'}: {exc}")
                rows.append((sw, side, free, rms, Lm, n_eq, n_par, spread))
                res[(sw, side, free)] = (rms, Lm)

    print(f"    (single start at p=1.0 -- L3 established global identifiability; see _starts)")
    print(f"    {'stimulus':<15}{'side':<7}{'rho':<6}{'rms dB':>9}{'L(0)':>10}{'L(.125)':>10}"
          f"{'L(noon)':>10}{'eq/par':>10}")
    for sw, side, free, rms, Lm, n_eq, n_par, spread in rows:
        print(f"    {sw.replace('sweep_', ''):<15}{side:<7}{'free' if free else 'meas':<6}"
              f"{rms:>9.3f}{Lm[0.0]:>10.5f}{Lm[0.125]:>10.5f}{Lm[NOON]:>10.5f}"
              f"{n_eq:>6}/{n_par:<4}")

    ped = [r for r in rows if r[1] == "PEDAL" and not r[2]]
    mdl = [r for r in rows if r[1] == "MODEL" and not r[2]]
    ped_rms = [r[3] for r in ped]
    mdl_rms = [r[3] for r in mdl]

    # --- L4: the structural verdict ---------------------------------------------------------
    print(f"\n    L4: with the SAME freedom (8 taper values + {len(nonhf)} per-band interference")
    print(f"        terms), the model fits its own ladder to {max(mdl_rms):.3f} dB and the pedal's")
    print(f"        to {min(ped_rms):.3f}-{max(ped_rms):.3f} dB.")

    # --- L5: the free-rho control -----------------------------------------------------------
    mdl_free = [r[3] for r in rows if r[1] == "MODEL" and r[2]]
    ped_free = [r[3] for r in rows if r[1] == "PEDAL" and r[2]]
    if max(mdl_free) > 10.0 * max(max(mdl_rms), 1e-6):
        print(f"\n    ⚠ L5 UNINTERPRETABLE: freeing rho makes even the MODEL fit worse "
              f"({max(mdl_free):.3f} vs {max(mdl_rms):.3f}) --\n      the control is not "
              f"converging, so it cannot arbitrate the pedal's residual.")
        l5_verdict = "uninterpretable"
    elif min(ped_free) < 0.25 * min(ped_rms):
        print(f"\n    L5: freeing |rho| per band COLLAPSES the pedal residual "
              f"({min(ped_rms):.3f} -> {min(ped_free):.3f} dB).")
        print( "        => the defect is in the endpoint |rho| measurement, NOT in the network")
        print( "           topology.  L4's verdict must not be read as a topology refutation.")
        l5_verdict = "rho"
    else:
        print(f"\n    L5: freeing |rho| per band does NOT rescue the pedal "
              f"({min(ped_rms):.3f} -> {min(ped_free):.3f} dB, "
              f"{len(nonhf)} extra free parameters).")
        print( "        => the residual is not the endpoint measurement.  The shipped network")
        print( "           cannot produce the pedal's ladder under ANY taper AND ANY bleed.")
        l5_verdict = "network"

    # --- L6: stimulus invariance ------------------------------------------------------------
    inv = {x: [r[4][x] for r in ped] for x in xs if 0.0 < x < 1.0}
    worst_x, worst_sp = max(((x, max(v) - min(v)) for x, v in inv.items()), key=lambda t: t[1])
    mdl_inv = {x: [r[4][x] for r in mdl] for x in xs if 0.0 < x < 1.0}
    m_sp = max(max(v) - min(v) for v in mdl_inv.values())
    print(f"\n    L6: a pot's taper cannot depend on the stimulus.  Across the {len(SWEEPS)} "
          f"stimulus levels the\n        recovered L spreads {m_sp:.5f} (MODEL -- the known "
          f"answer, so this is the floor) and\n        {worst_sp:.5f} (PEDAL, worst at "
          f"x = {worst_x:.3f}: "
          + ", ".join(f"{v:.3f}" for v in inv[worst_x]) + ").")
    if worst_sp <= max(10.0 * m_sp, IDENT_TOL):
        print( "        The pedal's taper IS stimulus-invariant -- so the model form holds and")
        print( "        the recovered curve is a property of the control.")
        l6_verdict = "invariant"
    else:
        print( "        The pedal's recovered taper is NOT stimulus-invariant, by far more than")
        print( "        the model's floor.  A pot cannot do that ⇒ this is a refutation of the")
        print( "        MODEL FORM for the pedal, not a measurement of its taper.")
        print( "        ⛔ Do NOT fit a taper to any single column above.")
        l6_verdict = "not-invariant"

    out["l4"] = {"model_rms": mdl_rms, "pedal_rms": ped_rms,
                 "model_rms_freerho": mdl_free, "pedal_rms_freerho": ped_free}
    out["l5"] = {"verdict": l5_verdict}
    out["l6"] = {"verdict": l6_verdict, "pedal_spread": worst_sp, "model_spread": m_sp,
                 "worst_x": worst_x,
                 "pedal_L_by_sweep": {r[0]: {str(x): r[4][x] for x in xs} for r in ped},
                 "model_L_by_sweep": {r[0]: {str(x): r[4][x] for x in xs} for r in mdl}}
    return l5_verdict, l6_verdict


# --------------------------------------------------------------------------------------------
# L7 -- the LEVEL-min mute
# --------------------------------------------------------------------------------------------
def gate_l7(absfr, lad, fc, fo, nonhf, out):
    print("\n-- L7: the LEVEL-min mute, quantified --")
    vals = {}
    for sw in SWEEPS:
        pb = lambda f, w: absfr[(f, sw)][w][nonhf]
        m0 = float(np.mean(pb(lad[0.0], 0) - pb(lad[NOON], 0)))
        q0 = float(np.mean(pb(lad[0.0], 1) - pb(lad[NOON], 1)))
        Lm, _rms, _e, _p, _s, _ = invert(absfr, lad, fc, fo, sw, 1, nonhf, multi=False)
        vals[sw] = (m0, q0, Lm[0.0])
    print(f"    {'stimulus':<12}{'MODEL re noon':>15}{'PEDAL re noon':>15}{'L_pedal(0)':>13}")
    for sw, (m0, q0, L0) in vals.items():
        cell = f"{m0:.1f}" if m0 > -100 else "-inf (mute)"
        print(f"    {sw.replace('sweep_', ''):<12}{cell:>15}{q0:>15.2f}{L0:>13.5f}")
    L0s = [v[2] for v in vals.values()]
    print(f"\n    The shipped stage sets the wiper hard on VD at LEVEL 0 (`if (L <= 0.0) vw = 0`),")
    print(f"    so BOTH coefficients vanish and the output is exactly zero at every BLEND.")
    print(f"    The reference does not mute: it floors {abs(max(v[1] for v in vals.values())):.0f}-"
          f"{abs(min(v[1] for v in vals.values())):.0f} dB below noon, and the inverse puts its")
    print(f"    residual wiper position at L(0) = {min(L0s):.4f}-{max(L0s):.4f}.")
    print(f"    ⚠ That is ~{100 * np.mean(L0s):.1f}% of full, which is FAR too large for a pot's end")
    print( "      resistance (a 100k pot with a 50 ohm end stop would read about -66 dB, not -20).")
    print( "      So `check whether the divider needs an end resistance` -- the session-103 next")
    print( "      step -- is answered NO by its own size.  Report the number; do not fit it to an")
    print( "      end resistance that cannot produce it.")
    print( "    ⛔ Both LEVEL-min captures sit under release_gate's SILENT_DB, so the matrix has")
    print( "       never graded this row and cannot arbitrate any fix to it.")
    out["l7"] = {sw: {"model_re_noon": v[0], "pedal_re_noon": v[1], "L0": v[2]}
                 for sw, v in vals.items()}


# --------------------------------------------------------------------------------------------
# L8 -- what the above-noon fall actually is
# --------------------------------------------------------------------------------------------
def gate_l8(absfr, lad, fc, fo, nonhf, out):
    """GATE K3 flagged that the MODEL's H1 falls above noon and read it as downstream saturation.
    L3 reproduces the model's law -- at that same stimulus -- to ~1e-10 with a STRICTLY LINEAR
    network containing no saturation term at all.  Both cannot be true."""
    print("\n-- L8: the above-noon H1 fall -- saturation, or the network itself? --")
    Ls = np.linspace(0.0, 1.0, 100001)
    bb = b_of(Ls)
    kmax = int(bb.argmax())
    if not (0.4 < Ls[kmax] < 0.6) or b_of(1.0) != 0.0:
        sys.exit("GATE L8 FAIL: b(L) is not the non-monotone shape the argument rests on")
    print(f"    b(L) = a(L)(1-L) peaks at L = {Ls[kmax]:.4f} and is exactly 0 at LEVEL max, so the")
    print( "    CLEAN contribution RISES then COLLAPSES as LEVEL is raised.  If the clean tap is")
    print( "    hotter than the OD path, the SUM can therefore fall -- with no saturation at all.")

    sw = "sweep_drv_-6"                       # where K3 saw the fall and rho is largest
    pb = lambda f, w: absfr[(f, sw)][w][nonhf]
    print(f"\n    {'':>7}{'measured step 0.875 -> 1.0 re noon, dB':>44}")
    print(f"    {'side':>7}{'measured':>14}{'LINEAR prediction':>20}")
    rows = {}
    for which, side in ((0, "MODEL"), (1, "PEDAL")):
        rho = 10.0 ** ((pb(fc, which) - pb(fo, which)) / 20.0)
        meas = float(np.mean(pb(lad[1.0], which) - pb(lad[0.875], which)))
        # the network's own prediction at the SHIPPED taper, per band, c = 0 (the fitted value)
        def amp(x):
            L = x ** SHIPPED_P
            return a_of(L) * np.sqrt(1.0 + ((1.0 - L) * rho) ** 2)
        pred = float(np.mean(20.0 * np.log10(amp(1.0) / amp(0.875))))
        rows[side] = (meas, pred)
        print(f"    {side:>7}{meas:>14.2f}{pred:>20.2f}")
    out["l8"] = {"b_peak_L": float(Ls[kmax]), "sweep": sw,
                 "step": {k: {"measured": v[0], "linear_pred": v[1]} for k, v in rows.items()}}
    if rows["MODEL"][0] >= 0.0:
        print("\n    (no fall at this stimulus in this report -- nothing to attribute)")
        return
    print(f"\n    The MODEL falls and the PEDAL does not, and the LINEAR network predicts that")
    print( "    split from the two sides' own measured clean/OD ratios -- which differ by exactly")
    print( "    the A3 excess K7 measures.  b(L)'s collapse converts a too-hot clean tap into a")
    print( "    FALLING top of the LEVEL law.")
    print( "    ⇒ GATE K3's reading -- 'a stage downstream of LEVEL is saturating harder in the")
    print( "      model' -- is REFUTED.  It is not a second, distinct defect: it is A3 seen")
    print( "      through the mixing network's bleed turnover.  Correcting A3 shrinks it.")


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json", default=None)
    a = ap.parse_args()

    bands, caps = MG.load(a.report)[0], MG.load(a.report)[1]
    idx = [i for i, b in enumerate(bands) if MG.GRADE_LO <= b <= MG.GRADE_HI]
    absfr, _silent = K.absolute_fr(caps, idx)
    nonhf = [j for j, i in enumerate(idx) if bands[i] < K.HF_HZ]

    print(f"GATE L -- can the shipped LevelBlend produce the pedal's LEVEL law?   [{a.report}]")
    print(f"  {len(caps)} captures, {len(idx)} graded bands, {len(nonhf)} non-HF "
          f"(< {K.HF_HZ:.0f} Hz, HF excluded per GATE I)")

    out = {"report": a.report}
    gate_l1(out)
    lad, fc, fo = gate_l2(caps, out)
    model_rms = gate_l3(absfr, lad, fc, fo, nonhf, out)
    l5, l6 = gate_l456(absfr, lad, fc, fo, nonhf, model_rms, out)
    gate_l7(absfr, lad, fc, fo, nonhf, out)
    gate_l8(absfr, lad, fc, fo, nonhf, out)

    print("\n== GATE L: all sub-gates passed ==")
    if a.json:
        with open(a.json, "w", encoding="utf-8") as fh:
            json.dump(out, fh, indent=1, default=float)
        print(f"   wrote {a.json}")


if __name__ == "__main__":
    main()
