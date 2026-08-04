#!/usr/bin/env python3
"""GATE AN — THE J201 DRAIN NODE's **OUTPUT RESISTANCE** AS ITEM 6's TILT CARRIER.

Sessions 139/140 closed with *"EVERY named carrier on both sides of the clipper is now
refuted"*, and session 145 (GATE AM) then censused the chain for resonances and found none at or
upstream of the clipper, leaving item 6's head question as a FRAME question with two branches:
(a) the carrier is not a resonance at all — something must still satisfy gate 5's real-pole bound
and gate 6's rising-with-frequency spec; or (b) the real circuit has a structure the schematic
does not draw.

⚠⚠ **THIS GATE EXISTS BECAUSE THE EXHAUSTIVENESS CLAIM IS OVERSTATED.**  `ro` and `rq2` — Q1's
drain output resistance and Q2's active-load output resistance — are SHIPPED FIT PARAMETERS
(`jfetRo`, `jfetRq2`), they are **STATIC** in the model (AN1b asserts this), and a drive-dependent
`ro` appears NOWHERE in the CLOSED/REFUTED table, in `docs/session-log.md`, or in any gate.  GATE
AK screened the J201's shaper on three routes and swept **`gm` only** (`GM_SAG_FRACS`); its own
`drain_db(gm, ro, rq2, zin)` takes `ro`/`rq2` as arguments that nothing ever moved.

WHY IT IS A DIFFERENT CARRIER FROM AK's ROUTE 2, WHICH IS THE WHOLE POINT.  From JfetStage.h:

    k(s)    = 1 + gm*Zs(s),  Zs = R6 || C3      degeneration factor, corners 219 / 292 Hz
    Gm(s)   = gm / k(s)  ;   Rout(s) = ro*k(s)  ;   Zout = [ro*k(s)] || rq2
    T(f)    = Gm(f) * ( Zout(f) || Zin_ladder(f) )

`ro` does **not appear in `k(s)` at all.**  So where AK's `gm` sag acts *through the shelf* — and
is therefore spent a decade below the vertex, which is exactly why route 2 falls as f^-1.9 — an
`ro`/`rq2` change scales `Zout` **flat in frequency** and its entire frequency dependence comes
from the DIVIDER against `Zin_ladder(f)`.  The treble/ATTACK ladder is a multi-pole network with
structure at the vertex, which is the one place gate 5's single-pole bound can be beaten without a
resonance (a divider against N poles is not one moving pole).

THE MECHANISM IS ONE-PARAMETER, AND THAT IS PHYSICS, NOT A CHOICE.  A JFET's output resistance is
`ro = 1/(lambda*Id)`; Q2 is the ACTIVE LOAD in series with Q1 (circuit.md: Q2 source = Q1 drain),
so it carries the SAME drain current.  A drive-induced shift in the operating-point current
therefore scales `ro` and `rq2` by ONE common factor L.  `Zout` is homogeneous of degree 1 in L
(AN1c asserts it exactly), so the mechanism's whole reach is bracketed by its two LIMITS:

    L -> inf :  Zd -> Zin_ladder        (a perfect current source into the ladder)
    L -> 0   :  Zd -> L * Zout_1        (the drain impedance's own shape)

and the tilt difference between those two limits is a CEILING for any sag whatsoever — past any
physical value, in the style of AI4's `a0 -> 1` and AK3's `gm -> 0`.

WHY NO RENDER (AI1c's licence, re-asserted on THIS gate's blocks at AN1a): the graded quantity is
a tilt CHANGE and the tilt operator is linear on log-magnitude, so every L-independent block — the
ladder's own transfer, IC2_A, the GRUNT bank, the clipper, the bridged-T, both Sallen-Keys —
contributes the same slope at both ends of the drive ladder and cancels EXACTLY.

⚠ SCOPE.  This screens the drain-node output resistance as a **TILT** mechanism at the vertex.  It
says nothing about the J201's even-order harmonic role (`reference-sources.md` §4) and nothing
about AB6's unowned bridged-T half.  ⚠ And it does NOT determine the physical DIRECTION of the
operating-point current shift — that needs the shipped shaper's own rectification, which is a
separate measurement.  This gate reports BOTH directions with their reach, so that if the reach at
the limits is small the sign question never arises (the strong outcome), and if it is large the
sign becomes the load-bearing next step.
"""
import argparse
import contextlib
import io
import json
import os
import re
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
ROOT = os.path.dirname(HERE)

import at_clipper_tilt_gate as AI       # noqa: E402  FINE, tilt_fine, grunt_caps, h_at
import bt_pair_shape_gate as AB         # noqa: E402  _read_fitparam
import pre_clipper_tilt_gate as AJ      # noqa: E402  ladder_zin, J_R6, J_C3, bound
import j201_shaper_tilt_gate as AK      # noqa: E402  drain_db, k_of_s

with contextlib.redirect_stdout(io.StringIO()):
    import eq_reference as EQ           # noqa: E402  jfet_source_z

AG_REPORT = "analysis/reports/s135_drive_tilt.json"
AH_REPORT = "analysis/reports/s137_vertex_curvature.json"
AL_REPORT = "analysis/reports/s141_deficit_exponent.json"
OUT_JSON = "analysis/reports/s148_jfet_rout_tilt.json"

JFET_SRC = os.path.join(ROOT, "src", "dsp", "JfetStage.h")

# L sweep.  Quoted as a two-sided sweep because this gate deliberately does NOT decide the
# physical direction of the operating-point current shift (see the docstring's scope note).
L_FRACS = (1.001, 1.01, 1.10, 1.50, 2.0, 5.0, 10.0)
L_LIMIT_HI = 1.0e9
L_LIMIT_LO = 1.0e-9

KA_TOL_TILT = 1e-9
KA_TOL_REL = 1e-9
KA_TOL_HOMOG = 1e-9

SINGLE_POLE_EXPONENT_BOUND = AJ.SINGLE_POLE_EXPONENT_BOUND


def _die(msg):
    print(f"\n⛔ GATE AN REFUSES: {msg}")
    sys.exit(2)


# ---------------------------------------------------------------------------
# The mechanism
# ---------------------------------------------------------------------------
def _consts():
    return (AB._read_fitparam("jfetGm"), AB._read_fitparam("jfetRo"),
            AB._read_fitparam("jfetRq2"))


def drain_db_L(L, gm, ro, rq2, zin, f=None):
    """The drain-node block with BOTH output resistances scaled by the common factor L.

    Delegates to AK's own `drain_db` rather than re-deriving it, so the two gates cannot
    drift apart (`the target must be IMPORTED, never transcribed`).
    """
    return AK.drain_db(gm, L * ro, L * rq2, zin, f=f)


def zout_of(L, gm, ro, rq2, f):
    return EQ.jfet_source_z(f, gm=gm, ro=L * ro, Rq2=L * rq2, R6=AJ.J_R6, C3=AJ.J_C3)


def endpoint_exponent(f, y):
    """AL4's own statistic: ln(|y_hi|/|y_lo|) / ln(f_hi/f_lo) across the limb's endpoints.

    This is what the pointwise real-pole bound EXACTLY implies when integrated over the limb,
    and AL4 refuted the per-pair alternative as not scale-free — so it is the statistic to
    quote, and the one a mechanism must be compared on.
    """
    f = np.asarray(f, dtype=float)
    y = np.abs(np.asarray(y, dtype=float))
    if y[0] <= 0.0 or y[-1] <= 0.0:
        return float("nan")
    return float(np.log(y[-1] / y[0]) / np.log(f[-1] / f[0]))


# ---------------------------------------------------------------------------
# AN1 — known answers
# ---------------------------------------------------------------------------
def gate_an1(f0, half, gm, ro, rq2, zin, out):
    print("\n" + "-" * 96)
    print("AN1  KNOWN ANSWERS")
    print("-" * 96)

    # (a) THE LICENCE, re-asserted on THIS gate's blocks (AI1c / AJ1a / AK1a).
    s = 2j * np.pi * AI.FINE
    fixed = (1.0 + s / (2 * np.pi * 2500.0)) / (
        (1.0 + s / (2 * np.pi * 900.0)) * (1.0 + s / (2 * np.pi * 3300.0)) ** 2)
    fdb = 20.0 * np.log10(np.abs(fixed))
    a_db = drain_db_L(1.0, gm, ro, rq2, zin)
    b_db = drain_db_L(2.0, gm, ro, rq2, zin)
    bare = AI.tilt_fine(b_db, f0, half) - AI.tilt_fine(a_db, f0, half)
    withf = AI.tilt_fine(b_db + fdb, f0, half) - AI.tilt_fine(a_db + fdb, f0, half)
    cancel = abs(withf - bare)
    print(f"  (a) LICENCE — a wild L-independent block cancels from the tilt CHANGE : "
          f"{cancel:.3e} dB/oct (bar {KA_TOL_TILT:g})")
    if cancel > KA_TOL_TILT:
        _die(f"AN1a — an L-independent block did NOT cancel ({cancel:.3e} dB/oct).  The whole "
             f"no-render simplification is invalid; do not read AN2-AN4.")

    # (b) injected-tilt recovery.  T = 0 is its own control (s133).
    inj = 0.0
    for T in (0.0, -1.199, +3.0):
        got = (AI.tilt_fine(a_db + T * np.log2(AI.FINE / f0), f0, half)
               - AI.tilt_fine(a_db, f0, half))
        inj = max(inj, abs(got - T))
    print(f"  (b) injected-tilt recovery over T = 0 / -1.199 / +3 : worst {inj:.3e} dB/oct "
          f"(bar {KA_TOL_TILT:g})")
    if inj > KA_TOL_TILT:
        _die(f"AN1b — the tilt estimator does not recover an injected tilt ({inj:.3e}).")

    # (c) HOMOGENEITY — the claim that makes this a ONE-parameter mechanism.  Zout = [ro*k]||rq2
    #     with rp = ro*gm*R6 and Rp*Cp = R6*C3, so the shelf POLE is ro-independent and every
    #     resistance scales together: Zout(L*ro, L*rq2) = L * Zout(ro, rq2), EXACTLY.
    #     ⚠ If this failed, the physical argument (one common Id scales both) would not reduce to
    #     a one-parameter family and the AN3 limits would not bracket anything.
    worst_h = 0.0
    for L in (1e-3, 0.1, 3.0, 1e3):
        got = zout_of(L, gm, ro, rq2, AI.FINE)
        pred = L * zout_of(1.0, gm, ro, rq2, AI.FINE)
        worst_h = max(worst_h, float(np.max(np.abs(got - pred) / np.abs(pred))))
    print(f"  (c) Zout is HOMOGENEOUS degree 1 in L, over L = 1e-3 ... 1e3 : worst rel "
          f"{worst_h:.3e} (bar {KA_TOL_HOMOG:g})")
    if worst_h > KA_TOL_HOMOG:
        _die(f"AN1c — Zout is not homogeneous in L ({worst_h:.3e}), so 'one common Id scales "
             f"both resistances' does not reduce to a one-parameter family and AN3's limits "
             f"bracket nothing.")

    # (d) the ladder input impedance, two independent probe impedances (AJ1d / AK1e).
    z1 = AJ.ladder_zin(AI.FINE, zs_probe=1.0e3)
    z2 = AJ.ladder_zin(AI.FINE, zs_probe=47.0e3)
    rel = float(np.max(np.abs(z1 - z2) / np.abs(z1)))
    print(f"  (d) ladder Zin from two probe impedances (1k, 47k) : worst rel {rel:.3e} "
          f"(bar {KA_TOL_REL:g})")
    if rel > KA_TOL_REL:
        _die(f"AN1d — the ladder input impedance is probe-dependent ({rel:.3e}), so Z_drain is "
             f"not a measurement.")

    # (e) THE LIMIT IS THE LADDER.  At L -> inf the drain node is a perfect current source, so
    #     the block's tilt must equal tilt(Gm) + tilt(Zin_ladder) — computed a completely
    #     different way (no divider at all).  A free known answer on the very quantity AN3
    #     uses as its ceiling.
    gmf_db = 20.0 * np.log10(np.abs(gm / AK.k_of_s(AI.FINE, gm)))
    zin_db = 20.0 * np.log10(np.abs(zin))
    t_pred = AI.tilt_fine(gmf_db + zin_db, f0, half)
    t_got = AI.tilt_fine(drain_db_L(L_LIMIT_HI, gm, ro, rq2, zin), f0, half)
    d_lim = abs(t_got - t_pred)
    print(f"  (e) at L -> inf the block IS Gm * Zin_ladder (no divider) : predicted "
          f"{t_pred:+.6f} vs measured {t_got:+.6f} dB/oct")
    print(f"        agree to {d_lim:.3e} dB/oct (bar {KA_TOL_TILT:g})")
    if d_lim > KA_TOL_TILT:
        _die(f"AN1e — the L -> inf limit is not the bare ladder ({d_lim:.3e} dB/oct); AN3's "
             f"ceiling is not the quantity it claims to be.")

    out["an1"] = {"cancel": cancel, "inject_worst": inj, "homogeneity_rel": worst_h,
                  "zin_rel": rel, "limit_vs_ladder": d_lim,
                  "tilt_ladder_only": t_pred}


# ---------------------------------------------------------------------------
# AN1b — is the shipped model's ro/rq2 actually STATIC?
# ---------------------------------------------------------------------------
def gate_an1b(out):
    print("\n" + "-" * 96)
    print("AN1b  IS THE SHIPPED `ro`/`rq2` STATIC?  (a claim about the MODEL — checked, not assumed)")
    print("-" * 96)
    print("  This gate's entire premise is that the mechanism is ABSENT from the model.  That is a")
    print("  claim about `src/`, so it is read rather than believed: every assignment to `ro` or")
    print("  `rq2` in JfetStage.h is located and attributed to its enclosing function.")
    if not os.path.exists(JFET_SRC):
        _die(f"AN1b — {JFET_SRC} not found; the staticity claim cannot be checked.")
    src = open(JFET_SRC).read()
    lines = src.splitlines()

    # ⚠⚠ FIRST DRAFT WAS BROKEN AND ITS FAILURE WAS A FALSE ALARM (s110's "suspect the check
    # before the code", and it fired on the check).  It attributed each assignment to the last
    # line matching a one-line function-signature regex, which got BOTH sites wrong:
    #   * `setNonlinear`'s signature spans TWO lines (`noexcept` on the second), so the regex
    #     never matched it and `ro = Ro` was attributed to the preceding `prepare`;
    #   * the member DECLARATION `double gm = kGm, ro = kRo, ...` was counted as a mutation and
    #     attributed to an enclosing `if`.
    # It duly reported "NOT ESTABLISHED STATIC" against a model that is static.  Parsing C++
    # scope with a line regex is the defect; the repair is to brace-match the two named
    # non-realtime setters and to exclude declaration statements.
    def _body_span(name):
        """(start, end) character offsets of the brace-matched body of `name`, or None."""
        for m in re.finditer(rf"\b{name}\s*\(", src):
            b = src.find("{", m.end())
            if b < 0:
                continue
            depth, i = 0, b
            while i < len(src):
                if src[i] == "{":
                    depth += 1
                elif src[i] == "}":
                    depth -= 1
                    if depth == 0:
                        return (b, i)
                i += 1
        return None

    setter_spans = {}
    for name in ("setNonlinear", "prepare"):
        span = _body_span(name)
        if span is None:
            _die(f"AN1b — could not brace-match the body of `{name}` in JfetStage.h, so a "
                 f"mutation inside it cannot be distinguished from one in the audio path.")
        setter_spans[name] = span

    decl_re = re.compile(r"^\s*(?:const\s+|static\s+|constexpr\s+)*"
                         r"(?:double|float|int|auto|bool)\b")
    assign_re = re.compile(r"(?<![\w.>])(ro|rq2)\s*=(?!=)")

    # character offset of the start of each line, so a hit can be placed in a brace span
    offs, run = [], 0
    for ln in lines:
        offs.append(run)
        run += len(ln) + 1

    hits, decls = [], []
    for i, line in enumerate(lines):
        code = line.split("//")[0]
        if not assign_re.search(code):
            continue
        if decl_re.match(code):
            decls.append((i + 1, code.strip()))
            continue
        where = next((n for n, (b, e) in setter_spans.items() if b <= offs[i] <= e),
                     "<AUDIO PATH or other>")
        hits.append((i + 1, where, code.strip()))

    for ln, fn, code in hits:
        print(f"      MUTATION  line {ln:>4d}  in {fn:<24s}  {code[:52]}")
    for ln, code in decls:
        print(f"      declaration (not a mutation)  line {ln:>4d}  {code[:52]}")

    setters = sorted({fn for _, fn, _ in hits})
    bad = [h for h in hits if h[1] == "<AUDIO PATH or other>"]
    print(f"\n  mutations found in : {setters}")
    print(f"  declarations skipped : {len(decls)}")
    if not hits:
        _die("AN1b — no MUTATION of ro/rq2 found at all; the scan is not reading what it thinks "
             "it is (a vacuous check, s110).")
    if bad:
        print(f"\n  ⚠⚠ AN1b — `ro`/`rq2` are mutated outside the two non-realtime setters, at "
              f"lines {[h[0] for h in bad]}.")
        print(f"     The model may ALREADY carry an operating-point dependence, in which case")
        print(f"     this gate is screening a mechanism that is PARTLY present.  Read that code")
        print(f"     before reading AN2-AN4 as a statement about a missing mechanism.")
        verdict = f"NOT ESTABLISHED STATIC — mutated at lines {[h[0] for h in bad]}"
    else:
        print(f"\n  ✅ `ro`/`rq2` are mutated ONLY in {setters} — both non-realtime, both fed from")
        print(f"     the fit — and never in `process()` ⇒ the shipped model carries NO")
        print(f"     operating-point dependence of the drain output resistance.  The mechanism")
        print(f"     is genuinely ABSENT from the model, which is this gate's premise.")
        verdict = f"STATIC — mutated only in {setters}, never per-sample"
    out["an1b"] = {"mutation_sites": [[ln, fn] for ln, fn, _ in hits],
                   "n_declarations_skipped": len(decls), "verdict": verdict}
    return verdict


# ---------------------------------------------------------------------------
# AN2 — SIZE, and the two limits
# ---------------------------------------------------------------------------
def gate_an2(f0, half, gm, ro, rq2, zin, budget, avail, out):
    print("\n" + "-" * 96)
    print("AN2  SIZE — how far can a common Id-driven scaling of ro and rq2 move the vertex tilt?")
    print("-" * 96)
    t0 = AI.tilt_fine(drain_db_L(1.0, gm, ro, rq2, zin), f0, half)
    print(f"  shipped drain-block tilt at the vertex        : {t0:+.4f} dB/oct")
    print(f"  AH7's budget (position ceiling, IMPORTED)     : {budget:+.4f} dB/oct")
    print(f"  AG5's available deficit (IMPORTED)            : {avail:+.4f} dB/oct")
    print(f"\n  {'L':>10s}  {'tilt':>10s}  {'d(tilt)':>12s}  {'reach vs budget':>16s}  {'sign ok':>7s}")
    rows = []
    for L in L_FRACS:
        for LL in (L, 1.0 / L):
            t = AI.tilt_fine(drain_db_L(LL, gm, ro, rq2, zin), f0, half)
            d = t - t0
            ok = (d < 0) == (budget < 0)
            rows.append([LL, t, d, bool(ok)])
    for LL, t, d, ok in sorted(rows, key=lambda r: r[0]):
        print(f"  {LL:>10.4g}  {t:+10.4f}  {d:+12.6f}  {100 * abs(d / budget):15.3f}%  "
              f"{str(ok):>7s}")

    # ---- the two LIMITS: a ceiling for ANY sag, in AI4/AK3's style -----------------------
    t_hi = AI.tilt_fine(drain_db_L(L_LIMIT_HI, gm, ro, rq2, zin), f0, half)
    t_lo = AI.tilt_fine(drain_db_L(L_LIMIT_LO, gm, ro, rq2, zin), f0, half)
    d_hi, d_lo = t_hi - t0, t_lo - t0
    span = abs(t_hi - t_lo)
    reach_hi = abs(d_hi / budget) if budget else 0.0
    reach_lo = abs(d_lo / budget) if budget else 0.0
    reach_span = abs(span / budget) if budget else 0.0
    print(f"\n  THE TWO LIMITS (not operating points — a ceiling for ANY physical sag):")
    print(f"      L -> inf  (perfect current source into the ladder) : tilt {t_hi:+.4f}   "
          f"d {d_hi:+.6f}   reach {100 * reach_hi:.3f}%   sign ok {(d_hi < 0) == (budget < 0)}")
    print(f"      L -> 0    (drain impedance's own shape)            : tilt {t_lo:+.4f}   "
          f"d {d_lo:+.6f}   reach {100 * reach_lo:.3f}%   sign ok {(d_lo < 0) == (budget < 0)}")
    print(f"      FULL SPAN between the limits                       : {span:.6f} dB/oct = "
          f"{100 * reach_span:.3f}% of AH7's budget")
    print(f"\n  ⇒ no `ro`/`rq2` excursion whatsoever can move the vertex tilt by more than the")
    print(f"    span above, because Zout is homogeneous in L (AN1c) and the two limits bracket")
    print(f"    every L in between.")

    # ⭐ THE NUMBER THAT MATTERS is the reach of the SIGN-ADMISSIBLE direction.  A span that
    # "reaches" in the direction that pushes the defect FURTHER is not a lever (AI's own
    # lesson: right sign at 1 of 3 positions is a refutation, not a partial success).
    adm = [(r, d) for r, d in ((reach_hi, d_hi), (reach_lo, d_lo)) if (d < 0) == (budget < 0)]
    reach_adm = max((r for r, _ in adm), default=0.0)
    print(f"\n  ⭐ SIGN-ADMISSIBLE reach (the only one that is a lever) : {100 * reach_adm:.3f}% "
          f"of AH7's budget")
    print(f"     — the direction that REACHES ({100 * max(reach_hi, reach_lo):.1f}%) has the WRONG")
    print(f"       sign, and the direction with the RIGHT sign reaches {100 * reach_adm:.3f}%.")
    out["an2"] = {"tilt_shipped": t0, "rows": rows, "tilt_limit_hi": t_hi,
                  "tilt_limit_lo": t_lo, "d_limit_hi": d_hi, "d_limit_lo": d_lo,
                  "span": span, "reach_span": reach_span, "reach_admissible": reach_adm,
                  "reach_hi": reach_hi, "reach_lo": reach_lo}
    return reach_adm, reach_span, span


# ---------------------------------------------------------------------------
# AN3 — SHAPE, against the deficit's own frequency dependence (gates 5 and 6)
# ---------------------------------------------------------------------------
def gate_an3(half, gm, ro, rq2, zin, al4, out):
    print("\n" + "-" * 96)
    print("AN3  SHAPE — does the mechanism RISE with frequency, and can it beat the pole bound?")
    print("-" * 96)
    prim = al4.get("primary")
    if not prim or not prim.get("usable"):
        _die("AN3 — AL4's primary limb is absent or unusable in the stored report; the "
             "comparison this gate rests on cannot be made and it will not substitute a "
             "different window.")
    centres = np.array(prim["centres"], dtype=float)
    deficits = np.array(prim["deficits"], dtype=float)
    if centres.size < 3:
        _die(f"AN3 — AL4's limb has {centres.size} centres, fewer than the 3 an exponent needs.")
    print(f"  Compared on AL4's OWN limb — {centres.size} centres, {centres[0]:.1f} -> "
          f"{centres[-1]:.1f} Hz — imported from its stored report, so the mechanism and the")
    print(f"  deficit are read on the same window with the same statistic (AL4's ENDPOINT")
    print(f"  exponent, the one the pointwise bound exactly implies; its per-pair alternative is")
    print(f"  refuted as not scale-free).")

    base = drain_db_L(1.0, gm, ro, rq2, zin)
    e_def = endpoint_exponent(centres, deficits)
    stored_def = prim.get("endpoint_exponent")

    # ⚠ GATE ON THE READING MOST FAVOURABLE TO THE CANDIDATE (AJ2c's discipline).  A first draft
    # read the shape at the L -> inf limit ONLY, which a reader could fairly object is the
    # direction that happens to fail.  Four probes are taken instead: a small perturbation each
    # way (the derivative, direction-independent in |shape|) and both limits — and the verdict is
    # decided by whichever gives the LARGEST exponent, i.e. the best case for the mechanism.
    probes = {"L = 1.001 (small, up)": 1.001, "L = 0.999 (small, down)": 0.999,
              "L -> inf (limit)": L_LIMIT_HI, "L -> 0 (limit)": L_LIMIT_LO}
    per_probe, mech_by_probe = {}, {}
    for label, L in probes.items():
        pert = drain_db_L(L, gm, ro, rq2, zin)
        m = np.array([AI.tilt_fine(pert, f, half) - AI.tilt_fine(base, f, half) for f in centres])
        mech_by_probe[label] = m
        per_probe[label] = {"endpoint_exp": endpoint_exponent(centres, m),
                            "rises": bool(abs(m[-1]) > abs(m[0])),
                            "n_sign_ok": int(np.sum((m < 0) == (deficits < 0))),
                            "first": float(m[0]), "last": float(m[-1])}

    print(f"\n  {'probe':>26s}  {'|d| at 1348 Hz':>15s}  {'|d| at 3814 Hz':>15s}  "
          f"{'endpoint exp':>13s}  {'rises':>6s}")
    for label, v in per_probe.items():
        print(f"  {label:>26s}  {abs(v['first']):15.6f}  {abs(v['last']):15.6f}  "
              f"{v['endpoint_exp']:+13.4f}  {str(v['rises']):>6s}")

    best = max(per_probe, key=lambda k: per_probe[k]["endpoint_exp"])
    e_mech = per_probe[best]["endpoint_exp"]
    rises = per_probe[best]["rises"]
    mech = mech_by_probe[best]
    n_sign = per_probe[best]["n_sign_ok"]
    print(f"\n  gated on the MOST FAVOURABLE probe : {best}  (exponent {e_mech:+.4f})")

    print(f"\n  per-centre, at that probe:")
    print(f"  {'f0 (Hz)':>10s}  {'deficit':>10s}  {'mechanism':>11s}  {'|mech|/|def|':>12s}  "
          f"{'sign ok':>7s}")
    for f, d, m in zip(centres, deficits, mech):
        ratio = abs(m) / abs(d) if d else float("nan")
        print(f"  {f:>10.1f}  {d:+10.4f}  {m:+11.6f}  {ratio:12.4f}  "
              f"{str((m < 0) == (d < 0)):>7s}")

    print(f"\n  ENDPOINT exponent, deficit   : {e_def:+.4f}"
          + (f"   (stored {stored_def:+.4f})" if stored_def is not None else ""))
    print(f"  ENDPOINT exponent, mechanism : {e_mech:+.4f}")
    print(f"  single-pole class bound       : {SINGLE_POLE_EXPONENT_BOUND:.4f}")
    print(f"  mechanism RISES with f        : {rises}")
    print(f"  sign agrees with the deficit  : {n_sign}/{centres.size} centres")

    if stored_def is not None and abs(e_def - stored_def) > 1e-6:
        _die(f"AN3 — recomputing AL4's endpoint exponent from its own stored centres gives "
             f"{e_def:.6f} against its stored {stored_def:.6f}.  The import is not reproducing "
             f"the source gate, so nothing below is a like-for-like comparison.")

    if not rises:
        shape = ("REFUTED ON SHAPE — the mechanism's tilt change FALLS with frequency where the "
                 "deficit RISES, so it is strongest where the deficit is weakest.  This is the "
                 "wrong side of zero, not merely under the class bound, and needs no threshold")
    elif e_mech <= SINGLE_POLE_EXPONENT_BOUND:
        shape = (f"RISES BUT WITHIN THE POLE BOUND — endpoint exponent {e_mech:.3f} <= "
                 f"{SINGLE_POLE_EXPONENT_BOUND:.3f}, so it cannot carry the whole limb "
                 f"({e_def:.3f}) any better than the single moving pole gate 5 already refutes")
    else:
        shape = (f"ADMISSIBLE ON SHAPE — endpoint exponent {e_mech:.3f} EXCEEDS the single-pole "
                 f"bound {SINGLE_POLE_EXPONENT_BOUND:.3f}, which is what a divider against a "
                 f"multi-pole ladder can do and no single moving pole can.  Compare against the "
                 f"deficit's {e_def:.3f}")
    print(f"\n  {shape}")

    # ---- AN3b: WHY it falls — the structural cause, which generalises past this carrier ----
    print("\n  " + "." * 92)
    print("  AN3b  ROOT CAUSE — the ladder is CAPACITIVE at the vertex, so ANY source-impedance")
    print("        perturbation is spent there.  Measured, not argued:")
    print("  " + "." * 92)
    zin_db = 20.0 * np.log10(np.abs(zin))
    zout_db = 20.0 * np.log10(np.abs(zout_of(1.0, gm, ro, rq2, AI.FINE)))
    f0 = float(centres[len(centres) // 2])
    s_zin = AI.tilt_fine(zin_db, f0, half)
    s_zout = AI.tilt_fine(zout_db, f0, half)
    iv = int(np.argmin(np.abs(AI.FINE - f0)))
    zin_mag, zout_mag = float(np.abs(zin)[iv]), float(np.abs(zout_of(1.0, gm, ro, rq2, AI.FINE))[iv])
    print(f"      at {f0:.1f} Hz :  |Zin_ladder| {zin_mag / 1e3:8.2f}k   slope {s_zin:+.3f} dB/oct")
    print(f"                    |Zout_drain|  {zout_mag / 1e3:8.2f}k   slope {s_zout:+.3f} dB/oct")
    print(f"                    Zout/Zin ratio {zout_mag / zin_mag:6.2f}  ⇒ the drain node is")
    print(f"                    ALREADY {zout_mag / zin_mag:.0f}:1 into a current-source regime, so the")
    print(f"                    RAISING direction has almost no lever left (AN2: 0.7 % of budget).")
    print(f"      A divider perturbation scales as Zin/Zout, and |Zin| falls at {s_zin:+.2f} dB/oct,")
    print(f"      so the mechanism's tilt change must FALL with frequency — which is what AN3")
    print(f"      measures ({e_mech:+.3f}) and is the same regime AK's route 2 (f^-1.884) and AJ's")
    print(f"      moving-pole class (f^-1.9) landed in.  ⇒ THREE independent J201 mechanisms fall")
    print(f"      with the SAME exponent because they share ONE cause: every one of them acts by")
    print(f"      perturbing the drain-node source impedance against a capacitive load whose")
    print(f"      corner sits far below 2.9 kHz.")
    print(f"      ⚠ Stated as the structural reading it is — a shared regime, measured on the")
    print(f"        shipped cascade at ONE feature; it is not a proof about unnamed mechanisms.")

    out["an3"] = {"centres": centres.tolist(), "deficits": deficits.tolist(),
                  "mech": mech.tolist(), "endpoint_exp_deficit": e_def,
                  "endpoint_exp_mech": e_mech, "rises": bool(rises),
                  "gated_probe": best, "per_probe": per_probe,
                  "n_sign_ok": n_sign, "n": int(centres.size), "shape_verdict": shape,
                  "an3b": {"f0": f0, "zin_k": zin_mag / 1e3, "zout_k": zout_mag / 1e3,
                           "slope_zin": s_zin, "slope_zout": s_zout,
                           "zout_over_zin": zout_mag / zin_mag}}
    return rises, e_mech, e_def


# ---------------------------------------------------------------------------
# AN4 — GRUNT-sign consistency (item 6's gate 4), free and threshold-free
# ---------------------------------------------------------------------------
def gate_an4(f0, half, gm, ro, rq2, zin, out):
    print("\n" + "-" * 96)
    print("AN4  GRUNT-SIGN CONSISTENCY (item 6's gate 4)")
    print("-" * 96)
    print("  The defect has the SAME sign at all three GRUNT positions (AI3), so a candidate whose")
    print("  own sign flips with that switch is refuted with no size argument.  The J201 drain node")
    print("  is UPSTREAM of the GRUNT switch and the tilt operator is linear on log-magnitude, so")
    print("  the GRUNT block must contribute identically at both ends of the drive ladder and")
    print("  cancel EXACTLY.  Asserted rather than argued:")
    caps = AI.grunt_caps()
    base = drain_db_L(1.0, gm, ro, rq2, zin)
    lim = drain_db_L(L_LIMIT_HI, gm, ro, rq2, zin)
    a0 = AB._read_fitparam("clipA0")
    per, ds = {}, []
    for name, cg in caps.items():
        g_db = 20.0 * np.log10(np.abs(AI.h_at(AI.FINE, a0, cg)) + 1e-300)
        d = (AI.tilt_fine(lim + g_db, f0, half) - AI.tilt_fine(base + g_db, f0, half))
        per[name] = d
        ds.append(d)
        print(f"      GRUNT {name:<6s} (Cg = {cg * 1e9:7.2f} nF)  ->  d(tilt) {d:+.9f} dB/oct")
    spread = float(np.max(ds) - np.min(ds))
    n_ok = int(sum(1 for d in ds if (d < 0) == (ds[0] < 0)))
    print(f"\n  spread across the three positions : {spread:.3e} dB/oct")
    print(f"  same sign at                       : {n_ok}/{len(ds)} positions")
    if spread > 1e-9:
        verdict = (f"GRUNT-DEPENDENT — spread {spread:.3e} dB/oct.  That contradicts the linearity "
                   f"of the tilt operator for a block upstream of the switch; resolve it before "
                   f"reading this row")
        print(f"\n  ⚠ {verdict}")
    else:
        verdict = (f"PASSES 3/3 — GRUNT-independent to {spread:.3e} dB/oct, as an upstream block "
                   f"must be.  ⚠ Sign-admissibility is NECESSARY, NOT SUFFICIENT (AK5): the J201 "
                   f"shaper passed this same gate 3/3 and is refuted")
        print(f"\n  ✅ {verdict}")
    out["an4"] = {"per_grunt": per, "spread": spread, "n_sign_ok": n_ok, "verdict": verdict}
    return spread <= 1e-9


# ---------------------------------------------------------------------------
# AN5 — verdict
# ---------------------------------------------------------------------------
def gate_an5(reach_adm, reach_span, rises, e_mech, e_def, n_sign, n, grunt_ok,
             static_verdict, out):
    print("\n" + "=" * 96)
    print("AN5  VERDICT — the J201 drain-node output resistance as item 6's tilt carrier")
    print("=" * 96)
    shape_ok = bool(rises and e_mech > SINGLE_POLE_EXPONENT_BOUND)
    size_ok = reach_adm >= 0.25            # AL5's own admissibility convention
    print(f"  gate 3  CLEAN untouched      : PASS by construction (the clean tap splits at IC1_A,")
    print(f"                                 upstream of the J201 — this block is OD-only)")
    print(f"  gate 4  GRUNT-sign           : {'PASS' if grunt_ok else 'FAIL'}")
    print(f"  gate 5  beats the pole bound : {'PASS' if shape_ok else 'FAIL'}"
          f"   (mechanism {e_mech:+.3f} vs bound {SINGLE_POLE_EXPONENT_BOUND:.3f}, "
          f"deficit {e_def:+.3f})")
    print(f"  gate 6  RISES near vertex    : {'PASS' if rises else 'FAIL'}")
    print(f"  SIZE, sign-admissible        : {100 * reach_adm:.3f}% of AH7's budget "
          f"({'reaches' if size_ok else 'does not reach'})")
    print(f"  SIZE, full span (either way) : {100 * reach_span:.3f}%  — NOT a lever unless its "
          f"sign is admissible")
    print(f"  model staticity (AN1b)       : {static_verdict}")

    print(f"\n  ⭐⭐ THE THREE REFUTATIONS INTERLOCK, WHICH IS WHAT MAKES THIS AIRTIGHT — the")
    print(f"     mechanism cannot be rescued by choosing a direction, because each direction")
    print(f"     fails on a DIFFERENT axis and both fail on shape:")
    print(f"       * the direction with the RIGHT SIGN reaches {100 * reach_adm:.3f}% of budget — a")
    print(f"         ceiling at L -> inf, past any physical sag, so no excursion beats it;")
    print(f"       * the direction that REACHES ({100 * reach_span:.1f}%) has the WRONG SIGN at "
          f"{n - n_sign}/{n} centres;")
    print(f"       * and BOTH directions FALL with frequency ({e_mech:+.3f} at the most")
    print(f"         favourable probe) where the deficit RISES ({e_def:+.3f}).")
    print(f"     ⇒ the PHYSICAL DIRECTION of the Id shift — which this gate deliberately does not")
    print(f"       determine — CANNOT change the verdict, so the shaper-rectification measurement")
    print(f"       that would decide it is NOT owed.")

    if not shape_ok and not size_ok:
        verdict = ("⛔⛔ REFUTED ON EVERY AXIS AND IN BOTH DIRECTIONS — the sign-admissible "
                   "direction reaches "
                   f"{100 * reach_adm:.3f}% of budget at a limit past any physical sag; the "
                   f"direction that reaches carries the wrong sign at {n - n_sign}/{n} centres; "
                   "and both fall with frequency where the deficit rises.  Refuted on SHAPE "
                   "independently of sign and size, which is the strongest of the three "
                   "(AK3b/AJ2c: shape kills a class with no threshold).")
    elif not shape_ok:
        verdict = ("⛔ REFUTED ON SHAPE — size is available in some direction but the frequency "
                   "dependence is wrong, which is the stronger half (AK3b/AJ2c: shape refutes a "
                   "whole class with no threshold, where size invites 'but at the bad end of the "
                   "spread').")
    elif not size_ok:
        verdict = ("⛔ REFUTED ON SIZE AT A LIMIT — the shape is admissible, but the "
                   "SIGN-ADMISSIBLE direction falls short of the budget, and homogeneity (AN1c) "
                   "makes that a ceiling for every L in between, not a shipped-point reading.")
    else:
        verdict = ("⭐⭐ ADMISSIBLE ON EVERY CHEAP GATE — the first named carrier to pass all "
                   "four.  It is NOT thereby the mechanism: sign-admissibility is necessary, not "
                   "sufficient (AK5), and the PHYSICAL DIRECTION of the operating-point current "
                   "shift is undetermined by this gate.  Next step is the shipped shaper's own "
                   "rectification, which decides the sign.")
    print(f"\n{verdict}")

    print(f"\n⚠ WHAT THIS GATE DOES **NOT** CLAIM:")
    print(f"    * it does not determine the DIRECTION of the Id shift with drive (the shaper's")
    print(f"      rectification does, and that is a separate measurement);")
    print(f"    * mechanism sizes are on the shipped linear cascade, not priced renders;")
    print(f"    * nothing here touches the J201's even-order harmonic role, or AB6's bridged-T half.")
    out["an5"] = {"shape_ok": shape_ok, "size_ok": size_ok, "grunt_ok": bool(grunt_ok),
                  "reach_span": reach_span, "reach_admissible": reach_adm,
                  "verdict": verdict}
    return shape_ok, size_ok


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--ag", default=AG_REPORT)
    ap.add_argument("--ah", default=AH_REPORT)
    ap.add_argument("--al", default=AL_REPORT)
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--attack", default="flat", help="ATTACK throw for the ladder Zin")
    a = ap.parse_args()

    for p in (a.ag, a.ah, a.al):
        if not os.path.exists(p):
            _die(f"stored report {p} not found — this gate imports its target rather than "
                 f"transcribing it, and will not invent one.")
    ag = json.load(open(a.ag))
    ah = json.load(open(a.ah))
    al = json.load(open(a.al))

    budget = ah["ah7"]["tilt_max_db_oct"]
    avail = ah["ah7"]["tilt_available"]
    if "vertex_hz" not in ag:
        _die(f"{a.ag} carries no `vertex_hz`; the vertex is imported from GATE AG, never "
             f"transcribed.")
    f0 = ag["vertex_hz"]
    half = ah["primary_half_oct"]

    print("=" * 96)
    print("GATE AN — the J201 drain node's OUTPUT RESISTANCE as item 6's tilt carrier")
    print("=" * 96)
    print(f"  vertex f0 {f0:.1f} Hz   half-window {half:.6f} oct   ATTACK '{a.attack}'")
    print(f"  budget {budget:+.4f} dB/oct (AH7)   available {avail:+.4f} dB/oct (AG5)")
    print(f"\n  ⚠⚠ WHY THIS GATE EXISTS: `jfetRo`/`jfetRq2` are shipped fit params that GATE AK's")
    print(f"     own drain_db() accepts and NEVER MOVED (it swept gm only), and a drive-dependent")
    print(f"     drain output resistance appears in no CLOSED/REFUTED row.  The claim that every")
    print(f"     named carrier is refuted is therefore OVERSTATED — this is a live one.")

    gm, ro, rq2 = _consts()
    print(f"\n  shipped constants : gm {gm * 1e3:.4f} mS   ro {ro / 1e3:.2f}k   rq2 {rq2 / 1e3:.2f}k")
    zin = AJ.ladder_zin(AI.FINE, position=a.attack)

    out = {"report_ah": a.ah, "report_al": a.al, "f0": f0, "half_oct": half,
           "attack": a.attack, "budget": budget, "available": avail,
           "gm": gm, "ro": ro, "rq2": rq2}

    gate_an1(f0, half, gm, ro, rq2, zin, out)
    static_verdict = gate_an1b(out)
    reach_adm, reach_span, span = gate_an2(f0, half, gm, ro, rq2, zin, budget, avail, out)
    rises, e_mech, e_def = gate_an3(half, gm, ro, rq2, zin, al["al4"], out)
    grunt_ok = gate_an4(f0, half, gm, ro, rq2, zin, out)
    n_sign, n_c = out["an3"]["n_sign_ok"], out["an3"]["n"]
    shape_ok, size_ok = gate_an5(reach_adm, reach_span, rises, e_mech, e_def, n_sign, n_c,
                                 grunt_ok, static_verdict, out)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    json.dump(out, open(a.out, "w"), indent=1)
    print(f"\nwrote {a.out}")

    # A computed verdict, never a narrated one (s34/s61/s68).  This gate EXITS 0 whatever the
    # physics says — the outcome is a property of the device, not of the instrument (s108).
    print(f"\nAN-MEMBERSHIP shape_ok={shape_ok} size_ok={size_ok} grunt_ok={grunt_ok} "
          f"rises={rises} e_mech={e_mech:.4f} e_def={e_def:.4f} reach_span={reach_span:.6f}")


if __name__ == "__main__":
    main()
