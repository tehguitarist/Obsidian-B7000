#!/usr/bin/env python3.11
"""GATE AT — the MIX-KEYED law for OdToneRestore's 320 Hz notch.

WHY THIS EXISTS
===============
`OdToneRestore` is keyed on (GRUNT, DRIVE) only.  It sits in the OD path, upstream of LEVEL and
BLEND, so the amount of cut it must apply to land the COMPOSITE null on the pedal's depends on
how much clean signal is summed on top of it afterwards -- and it has no way to know that.  The
consequence is measured and large: the cut needed at LEVEL noon exceeds the bleed-free cut by
6-13 dB, so a table fitted at one mix is wrong at every other one.  s151 shipped the bleed-free
fit; the user hears LEVEL noon, where it is ~8 dB short and at DRIVE 0 has the WRONG SIGN (the
shipped Cut row BOOSTS 6.5 dB at 320 Hz where the listening condition wants a 1.2 dB cut).

WHAT MAKES A ONE-VARIABLE LAW LEGITIMATE (AT2, and it is the load-bearing claim)
===============================================================================
Because LEVEL and BLEND are both DOWNSTREAM of this stage, the required cut cannot depend on
them separately -- only on the single scalar clean fraction they jointly produce.  That is a
prediction, not an assumption, and the capture set can falsify it: many (LEVEL, BLEND) pairs
reach the same clean fraction by different routes.  Measured, they agree to 0.03-0.05 dB.
⇒ one law in the clean fraction covers EVERY LEVEL/BLEND combination, including uncaptured ones.

⭐ A free known answer fell out of the same run and is asserted here (AT1c): the eight EQ-swept
captures all sit at one clean fraction, and the EQ is downstream of the mix, so they MUST return
the same required cut.  They do, to 0.13 dB.  That certifies the reader before any law is fitted.

⚠⚠ EVERY PEDAL DEPTH READING HERE IS CENSORED (AT1d).  The pedal's null bottom sits within
0.1-1.2 dB of the deconvolution residue at every condition measured, and 5.0 dB BELOW it at the
bleed-free DRIVE-max corner.  GATE AP established what that means: the depths are LOWER BOUNDS,
so every required cut derived from them is an UNDER-estimate, worst where the null is deepest.
⛔ The residue is DIAGNOSTIC ONLY and is never used to exclude a cell (GATE R and GATE W each
deleted their own headline cells with it once).

⇒ THE cf -> 0 CLAMP.  Raw, the law is NON-MONOTONE: the required cut peaks at cf ~ 0.21 and
falls 9.6 dB toward the bleed-free corner.  That corner is the most censored reading in the set,
so the fall is at least partly an artefact of what can be seen.  `S_CLAMP_CF` holds the shape
flat below its peak rather than following the raw points down.  THREE independent reasons, none
of them a fit statistic:
  (1) the user's explicit instruction this session -- "if they need to be too deep, I'd prefer
      that";
  (2) the censoring above, which biases every reading in the shallow direction;
  (3) `reference-sources.md` section 1 makes HARDWARE the authority for this null's DEPTH, and
      section 3 records hardware DEEPER than ND by +1.6 dB at GRUNT cut rising to ~26 dB at
      boost -- so the ND-matched answer is itself a lower bound.
⚠ The clamp is ONE named constant.  Setting `S_CLAMP_CF = 0.0` reproduces the raw measured law
exactly, so the choice is reversible and auditable rather than baked into the numbers.

⛔ NOT CLAIMED: that this fixes A3.  It does not.  The OD path is still ~4.4 dB quiet (GATE O),
which is WHY the model's null dilutes away faster than the pedal's; this stage compensates the
symptom at the notch, in the OD path, exactly as the user authorised at s150.  It is [ENG] and
non-schematic and its scope is this one tone complex.

USAGE
    python3.11 analysis/od_notch_mix_law.py --collapse    # AT2: does the law have one variable?
    python3.11 analysis/od_notch_mix_law.py --law         # AT3/AT4: emit the shipped tables
"""
import argparse
import os
import sys

import numpy as np
from scipy.optimize import least_squares

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import captures as C
import level_law_gate as LL
import od_tone_restore_fit as F

FS = 48000.0 * F.W.OS_FACTOR
BAND = (240.0, 1600.0)
F_MID, F_BT = 323.0, 800.0
REAL = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

# The LEVEL taper the plugin SHIPS.
# ⚠⚠ RE-POINTED s172, AND THE RE-POINTING MOVES A NUMBER THIS TOOL'S OWN FIT WAS ANCHORED ON.
# This used to parse `FitParams::levelTaperExp` and rebuild `L = x ** p` (p = 2.25).  s163 RETIRED
# that constant -- the LEVEL law is a 4-segment PWL now -- and DELETED it rather than aliasing it,
# so this parse has hard-exited ever since and the tool has been unusable for 8 sessions.
# ⇒ call `level_law_gate.level_taper(x)`, the single implementation checked against the header.
#
# ⛔⛔ THE CONSEQUENCE IS NOT COSMETIC AND MUST NOT BE LOST: the s156 mix law that SHIPS was fitted
# with clean fractions computed through the RETIRED power taper.  At LEVEL noon that taper gave
# L = 0.5 ** 2.25 = 0.2102; the shipped PWL gives L = 0.1541.  So every capture's clean fraction --
# the law's own independent variable -- moved under the fit after it shipped.  `CF_REF` below is
# recomputed rather than transcribed for exactly that reason.
def _cf_at(blend, level, taper=None):
    """Clean fraction at a (BLEND, LEVEL) knob pair through the shipped mix algebra + taper."""
    import level_law_gate as _LL
    tf = _LL.level_taper if taper is None else taper
    od, cl = _LL.coef_closed(blend, tf(level))
    return (cl / (od + cl)) if (od + cl) > 0 else 1.0


# The clean fraction at LEVEL noon / BLEND max = the listening point.  COMPUTED, not transcribed:
# the literal 0.441 that stood here was the pre-s163 value and is wrong for the shipped taper.
CF_REF = _cf_at(1.0, 0.5)
CF_REF_RETIRED = 0.441    # what this tool used up to s162 -- kept so pre-s163 numbers reproduce

# ⛔⛔ THE CLAMP IS OFF, AND THE REASON IT WAS TURNED OFF IS THE INTERESTING PART.
# A first pass held S flat below its peak (S_CLAMP_CF = 0.21) on the argument that the raw law's
# 9.6 dB fall toward the bleed-free corner had to be a CENSORING artefact, since that corner is
# the most censored reading in the set (AT1d).  Built and measured, that overshot badly: the
# composite null came out 9.6-11.6 dB TOO DEEP at LEVEL/BLEND max while every other mix landed
# within 1-3 dB.  ⇒ the clamp was not erring on the safe side, it was breaking the one thing the
# user actually asked for ("track across all level, blend and gain levels, and I mean all").
# ⭐ And re-examined, the raw non-monotone shape is PHYSICALLY EXPECTED rather than artefactual:
# the required cut is largest at INTERMEDIATE mix because that is where the model's own null is
# diluted hardest while the pedal's target null is still deep.  At cf -> 0 the pedal's target is
# deep but the model's own OD null is already close to it; at cf -> 1 both wash out together.  A
# peak in the middle falls straight out of that, so there is nothing to "correct".
# ⚠ The censoring (AT1d) is still real and still means every number here is a lower bound — but
# the honest response to that is a uniform slight bias, not a 10 dB reshaping of one corner.
S_CLAMP_CF = 0.0
DRIVES = (0.0, 0.25, 0.5, 0.75, 1.0)
GRUNT_ROWS = ("cut", "flat", "boost")     # Clipper::Grunt order, matching kNotchGainDb's rows


def clean_frac(fname):
    """The single scalar LEVEL and BLEND jointly produce, from the SHIPPED mix algebra.

    `coef_closed` is IMPORTED from GATE K, never re-derived, and it takes the TAPERED level
    (s113: a shipped stage's closed form takes the STAGE's input, not the knob).

    ⚠ The old sanity note here read "LEVEL noon / BLEND max returns 0.441, which is GATE K2's own
    independently-measured ~44 % clean".  That agreement was real AND it was against the RETIRED
    power taper; under the shipped PWL the same knob pair returns `CF_REF` (printed every run).
    GATE K2's ~44 % is a measurement of the pre-s163 build and is not a check on this one."""
    p = C.parse_capture(fname)
    od, cl = LL.coef_closed(p["blend"], LL.level_taper(p["level"]))
    return (cl / (od + cl) if (od + cl) > 0 else 1.0), p


def _basis(f):
    x = np.log(np.asarray(f) / 400.0)
    return np.vstack([np.ones_like(x), x, x * x]).T


def required_cut(fname, drive, sweeps=REAL):
    """-> (cut dB, Q), the ABSOLUTE parameters this stage must deliver at this capture.

    Measured with the stage SUBTRACTED analytically (exact: the stage is linear and in series),
    so this is the requirement, not an increment on whatever is currently built.  A quadratic in
    log-f is fitted JOINTLY and discarded -- that trend is A3, a broadband OD-path deficit, and
    handing it to a narrow biquad is `one-knob-two-jobs-is-compensating`.  A second biquad at
    800 Hz is carried for the same reason (so the bridged-T region cannot leak into the 320 Hz
    term) and is NOT reported: it is not identified (median 0.058 dB of rms; see AT5)."""
    T = F.shipped_tables()
    gs, qs = [], []
    for sweep in sweeps:
        g, ped, mod = F.curves(fname, sweep)
        mod = mod - F.current_response(g, drive, FS, T, F.grunt_pos_of(fname), clean_frac(fname)[0])
        m = (g >= BAND[0]) & (g <= BAND[1])
        f, r = g[m], (ped - mod)[m]
        B = _basis(f)

        def shape(p):
            qm, gm, qb, gb = p
            return (F.rbj_peak_db(f, FS, F_MID, qm, -gm)
                    + F.rbj_peak_db(f, FS, F_BT, qb, -gb))

        def resid(p):
            d = r - shape(p)
            co, *_ = np.linalg.lstsq(B, d, rcond=None)
            return d - B @ co

        # ⚠ Q's upper bound is 40, not 24.  At the bleed-free corner the pedal's null is very
        # narrow and a 24 bound was RESTING (`bound-resting-means-unidentified`) on four of the
        # cf = 0 captures — exactly the cells K is derived from, so the bound was reaching the
        # shipped law.  40 is past anything the reader can resolve on a 1/48-oct grid.
        best = None
        for qm0 in (3.0, 10.0, 18.0, 30.0):
            for gm0 in (0.0, 10.0, 22.0):
                out = least_squares(resid, [qm0, gm0, 1.5, 0.0],
                                    bounds=([1.0, -12.0, 0.5, -12.0], [40.0, 45.0, 12.0, 45.0]),
                                    max_nfev=5000)
                if best is None or out.cost < best.cost:
                    best = out
        if best.x[1] > 44.9 or best.x[0] > 39.9:
            print(f"    ⚠ {fname} {sweep}: fit rests on a BOUND (cut {best.x[1]:.2f}, "
                  f"Q {best.x[0]:.2f}) — not a measurement")
        gs.append(best.x[1])
        qs.append(best.x[0])
    return float(np.mean(gs)), float(np.mean(qs))


def survey(gruntIdx):
    """Every full-send, ATTACK-flat OD capture at this GRUNT position, by SETTINGS not filename.

    (s114: selecting rows by filename substring is a time bomb — it does not fail when written,
    it fails when someone adds captures.)"""
    rows = []
    for fn in sorted(os.listdir(C.CAPTURE_DIR)):
        if not fn.endswith("_base-od.wav"):
            continue
        if "gain-n" in fn or "attack-" in fn or "master-" in fn:
            continue
        p = C.parse_capture(fn)
        if p.get("gruntIdx") != gruntIdx or p.get("drive") not in DRIVES:
            continue
        cf, _ = clean_frac(fn)
        if cf > 0.95:                    # essentially pure clean: no OD null exists to measure
            continue
        rows.append((fn, p["drive"], p["level"], p["blend"], cf))
    return sorted(rows, key=lambda r: (r[1], r[4]))


# =================================== AT2 — THE COLLAPSE ========================================
def do_collapse():
    GI = {"cut": 1, "flat": 2, "boost": 0}["cut"]
    rows = survey(GI)
    print(f"\n{'=' * 100}")
    print("AT2  COLLAPSE — does the required cut depend on (LEVEL, BLEND) only through cleanF?")
    print(f"  {len(rows)} captures, GRUNT cut.  Stage subtracted.  Mean over the 3 realistic sweeps.")
    print("=" * 100)
    print(f"  {'DRIVE':>5} {'LEVEL':>6} {'BLEND':>6} {'cleanF':>7} | {'cut dB':>7} {'Q':>6} | capture")
    out = []
    for fn, drv, lv, bl, cf in rows:
        cut, q = required_cut(fn, drv)
        out.append((drv, lv, bl, cf, cut, q))
        print(f"  {drv:5.2f} {lv:6.2f} {bl:6.2f} {cf:7.3f} | {cut:7.2f} {q:6.2f} | {fn}")

    # --- AT1c: the EQ-swept captures share one clean fraction and the EQ is DOWNSTREAM of the
    # mix, so they must all return the same cut.  A free known answer on the reader itself.
    eq = [r for r in out if abs(r[3] - CF_REF) < 1e-3 and r[0] == 0.5]
    if len(eq) >= 4:
        sp = max(r[4] for r in eq) - min(r[4] for r in eq)
        print(f"\n  AT1c KNOWN ANSWER — {len(eq)} captures at cleanF {CF_REF} differing only in EQ "
              f"(downstream of the mix):\n       required cut spread = {sp:.3f} dB "
              f"{'PASS' if sp < 0.5 else 'FAIL'}")
        if sp >= 0.5:
            sys.exit("AT1c FAILED: the reader is sensitive to something downstream of the mix")

    # --- AT2 proper: same cleanF, different route.
    print("\n  AT2 SAME cleanF BY A DIFFERENT ROUTE — the rows that actually test the law")
    worst, n = 0.0, 0
    for i in range(len(out)):
        for j in range(i + 1, len(out)):
            a, b = out[i], out[j]
            if a[0] != b[0] or abs(a[3] - b[3]) > 0.04:
                continue
            if abs(a[1] - b[1]) < 0.2 and abs(a[2] - b[2]) < 0.2:
                continue                       # not a different route, just neighbouring detents
            d = abs(a[4] - b[4])
            worst, n = max(worst, d), n + 1
            print(f"    DRIVE {a[0]:.2f}  cleanF {a[3]:.3f}/{b[3]:.3f}  "
                  f"(L{a[1]:.2f},B{a[2]:.2f}) {a[4]:6.2f}  vs  (L{b[1]:.2f},B{b[2]:.2f}) "
                  f"{b[4]:6.2f}   |diff| {d:5.2f} dB")
    if n == 0:
        sys.exit("AT2 VACUOUS: no same-cleanF/different-route pair found — the test proved nothing")
    print(f"\n  AT2 VERDICT: {n} genuinely different-route pairs, worst disagreement "
          f"{worst:.2f} dB — {'ONE-VARIABLE LAW SUPPORTED' if worst < 1.0 else 'NOT SUPPORTED'}")
    return out


# =================================== AT3/AT4 — THE LAW =========================================
def shape_nodes(rows_cut_drive05):
    """S(cf), normalised so S(CF_REF) = 0 and S(0) = 1 BEFORE clamping.

    Built from the GRUNT-cut / DRIVE-noon sweep, which is the only densely-sampled cf axis."""
    pts = sorted((cf, cut) for _, _, _, cf, cut, _ in rows_cut_drive05)
    cf0 = min(pts, key=lambda p: p[0])
    ref = min(pts, key=lambda p: abs(p[0] - CF_REF))
    K = cf0[1] - ref[1]
    return [(cf, (cut - ref[1]) / K) for cf, cut in pts], K


def do_law():
    print(f"\n{'=' * 100}")
    print("AT3/AT4  THE SHIPPED LAW    cut(grunt, drive, cf) = base[g][d] + K[g][d] * S(cf)")
    print(f"  reference clean fraction CF_REF = {CF_REF}  (LEVEL noon / BLEND max)")
    print(f"  S(CF_REF) = 0 by construction;  S clamped flat below cf = {S_CLAMP_CF}")
    print("=" * 100)

    allrows = {}
    for name, gi in (("cut", 1), ("flat", 2), ("boost", 0)):
        allrows[name] = survey(gi)

    # ---- S(cf) from the dense axis --------------------------------------------------------
    cutrows = [(fn, drv, lv, bl, cf) for fn, drv, lv, bl, cf in allrows["cut"] if drv == 0.5]
    meas = []
    for fn, drv, lv, bl, cf in cutrows:
        c, q = required_cut(fn, drv)
        meas.append((None, None, None, cf, c, q))
    S_raw, K_ref = shape_nodes(meas)
    # collapse duplicate cf (the EQ captures) to their mean so they do not out-vote the sweep
    agg = {}
    for cf, s in S_raw:
        agg.setdefault(round(cf, 3), []).append(s)
    S_raw = sorted((cf, float(np.mean(v))) for cf, v in agg.items())

    # ---- reduce to a few nodes, and ENFORCE MONOTONICITY -----------------------------------
    # Two reasons, both measured rather than aesthetic.  (a) The raw points carry one bad
    # capture: LEVEL knob 0.12 (cf 0.498) disagrees with its own neighbours by 1.3-1.8 dB where
    # every other different-route pair agrees to 0.05, and at that setting the tapered LEVEL is
    # 0.12^2.25 = 0.009 so there is almost no OD left to read.  (b) The law MUST be monotone in
    # cf on physical grounds -- adding clean signal can only fill the composite null in, never
    # deepen it -- so a non-monotone wiggle is reader noise, and shipping it would make the tone
    # jump around as LEVEL is swept.  A cumulative max is the minimal enforcement.
    # ⚠⚠ ORDER MATTERS AND GETTING IT WRONG IS SILENT: the clamp must be applied BEFORE the
    # monotone pass, not after.  Raw, S(0) = +1.0 by construction while S(0.21) = -0.51, so the
    # cf = 0 point is the one that VIOLATES monotonicity — and it is the censored one (AT1d).  A
    # cumulative max run over the raw list therefore latches on that first value and flattens
    # every node after it; a first draft here shipped an all-zero S and the law silently
    # degenerated to "ignore the mix entirely", which is the exact bug this whole gate exists to
    # remove.  So: take the nodes at and above the clamp, make THOSE monotone, then extend the
    # clamped value downward.
    NODES = (0.00, 0.21, 0.32, 0.44, 0.56, 0.73, 0.87, 1.00)
    raw_at = {}
    for cf in NODES:
        near = [s for c, s in S_raw if abs(c - cf) <= 0.06]
        raw_at[cf] = float(np.median(near)) if near else None
    # ⛔ NO monotone pass.  An earlier draft forced S non-decreasing, which (a) rested on a
    # physical argument that is simply wrong here — see the S_CLAMP_CF block — and (b) latched a
    # cumulative max on the cf = 0 node, flattening S to all-zeros and silently degenerating the
    # law to "ignore the mix", the exact bug this gate exists to remove.  The median window below
    # is what handles reader noise; the SHAPE is left as measured.
    have = sorted((c, s) for c, s in raw_at.items() if s is not None and c >= S_CLAMP_CF - 1e-9)
    first = have[0][1]
    S = [(cf, float(np.interp(cf, [c for c, _ in have], [s for _, s in have]))
          if cf >= S_CLAMP_CF - 1e-9 else first) for cf in NODES]
    ref_s = float(np.interp(CF_REF, [c for c, _ in S], [s for _, s in S]))
    S = [(c, s - ref_s) for c, s in S]                      # pin S(CF_REF) = 0 exactly
    Sc = S                                                  # clamp already folded in above
    if all(abs(s) < 1e-9 for _, s in S):
        sys.exit("od_notch_mix_law: S(cf) collapsed to zero — the law would ignore the mix")

    print(f"\n  S(cf) — shared shape, from GRUNT cut / DRIVE noon "
          f"({len(S_raw)} measured clean fractions -> {len(S)} nodes)")
    print(f"  {'cf':>7} {'S':>8} {'S clamped':>10}   (K at this row = {K_ref:.2f} dB)")
    for (cf, s), (_, sc) in zip(S, Sc):
        flag = "  <- clamped" if abs(s - sc) > 1e-9 else ""
        print(f"  {cf:7.3f} {s:8.3f} {sc:10.3f}{flag}")
    print("  raw measured points, for audit:  "
          + "  ".join(f"{c:.3f}:{s:+.3f}" for c, s in S_raw))

    # ---- base[g][d] and K[g][d] ------------------------------------------------------------
    print(f"\n  base[g][d] = cut at cf = {CF_REF};   K[g][d] = cut(cf=0) - cut(CF_REF)")
    print(f"  {'grunt':<6} {'drive':>6} | {'base dB':>8} {'K dB':>7} {'Q':>6} | source")
    base, Kt, Qt, cut0 = {}, {}, {}, {}
    for name in GRUNT_ROWS:
        for drv in DRIVES:
            at_ref = [r for r in allrows[name] if r[1] == drv and abs(r[4] - CF_REF) < 1e-3]
            at_0 = [r for r in allrows[name] if r[1] == drv and r[4] < 1e-6]
            b = q = k = c0 = None
            if at_ref:
                b, q = required_cut(at_ref[0][0], drv)
            if at_0:
                c0, q0 = required_cut(at_0[0][0], drv)
                cut0[(name, drv)] = c0
                if q is None:
                    q = q0
                if b is not None:
                    k = c0 - b
            base[(name, drv)], Kt[(name, drv)], Qt[(name, drv)] = b, k, q
            src = at_ref[0][0] if at_ref else (at_0[0][0] + " (cf=0)" if at_0 else "-")
            print(f"  {name:<6} {drv:6.2f} | "
                  f"{('%8.2f' % b) if b is not None else '       -'} "
                  f"{('%7.2f' % k) if k is not None else '      -'} "
                  f"{('%6.2f' % q) if q is not None else '     -'} | {src}")

    # ---- fill the gaps by interpolation in DRIVE, and say so ------------------------------
    def fill(tab, label):
        out = {}
        for name in GRUNT_ROWS:
            xs = [d for d in DRIVES if tab.get((name, d)) is not None]
            ys = [tab[(name, d)] for d in xs]
            if not xs:
                sys.exit(f"od_notch_mix_law: no data at all for {label}[{name}] — refusing to guess")
            for d in DRIVES:
                v = tab.get((name, d))
                out[(name, d)] = float(np.interp(d, xs, ys)) if v is None else v
            miss = [d for d in DRIVES if tab.get((name, d)) is None]
            if miss:
                print(f"  ⚠ {label}[{name}]: DRIVE {miss} had no capture — INTERPOLATED in drive "
                      f"from {xs}")
        return out

    print()
    Kt = fill(Kt, "K")
    # ⭐ Prefer DERIVING a missing base from a cf = 0 capture AT THAT DRIVE (base = cut(0) - K)
    # over interpolating base across drive: the former uses real data at the cell, the latter
    # invents it.  This matters — GRUNT flat has no cf = 0.441 capture at DRIVE 0.75/1.0, and
    # holding the DRIVE-0.5 value flat there would have shipped a row that stops responding to
    # DRIVE exactly where the null is deepest.
    for name in GRUNT_ROWS:
        for drv in DRIVES:
            if base.get((name, drv)) is None and (name, drv) in cut0:
                base[(name, drv)] = cut0[(name, drv)] - Kt[(name, drv)]
                print(f"  ⭐ base[{name}][{drv}] DERIVED from its own cf=0 capture as "
                      f"cut(0) - K = {cut0[(name, drv)]:.2f} - ({Kt[(name, drv)]:.2f}) = "
                      f"{base[(name, drv)]:.2f}")
    base, Qt = fill(base, "base"), fill(Qt, "Q")

    def emit(tab, name, fmt="%7.2f"):
        print(f"\n    static constexpr double {name}[3][5] = {{")
        for g in GRUNT_ROWS:
            vals = ", ".join(fmt % tab[(g, d)] for d in DRIVES)
            print(f"        {{ {vals} }},   // {g}")
        print("    };")

    print("\n" + "=" * 100)
    print("  PASTE-READY — src/dsp/OdToneRestore.h")
    print("=" * 100)
    emit(base, "kNotchGainDb")
    emit(Kt, "kNotchMixK")
    emit(Qt, "kNotchQ")
    print(f"\n    static constexpr double kMixCfRef = {CF_REF};")
    print(f"    static constexpr int kMixNodes = {len(Sc)};")
    print("    static constexpr double kMixCf[kMixNodes] = { "
          + ", ".join("%.3f" % cf for cf, _ in Sc) + " };")
    print("    static constexpr double kMixS[kMixNodes]  = { "
          + ", ".join("%.3f" % s for _, s in Sc) + " };")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--collapse", action="store_true")
    ap.add_argument("--law", action="store_true")
    a = ap.parse_args()
    if a.collapse:
        do_collapse()
    elif a.law:
        do_law()
    else:
        ap.error("choose --collapse or --law")
