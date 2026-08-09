#!/usr/bin/env python3.11
"""GATE BT — `OdToneRestore`'s mix law at the BLEED-FREE CORNER, priced by RENDER.

WHY THIS EXISTS
---------------
Open item 10, action-list item (5).  s192 localised the stage's remaining defect precisely:

  * at the LISTENING mix the table is RIGHT — a DEPTH objective reproduces it to 0.54 dB rms and
    an independent CURVE objective to 1.57 dB, every residual small and positive;
  * at the BLEED-FREE CORNER it is WRONG, and the error tracks how far the mix law EXTRAPOLATES
    that row's cut upward (`corr(residual, K*S) = -0.904`).  Boost is the only row whose
    `kNotchMixK` is POSITIVE, so it is extrapolated furthest up, and it over-cuts by 10-16 dB.

⇒ the subject is `kNotchMixK`'s CORNER behaviour, not the base table (s192's own words).

WHAT IS NEW HERE, AND WHY GATE AP COULD NOT DO IT
-------------------------------------------------
GATE AP evaluates a candidate ANALYTICALLY: `composite = mod_off + rbj_peak_db(gain)`.  That is
exact for the OD BRANCH — the stage is a linear biquad in series, so its dB response subtracts
exactly (s151's `--stage-off` argument) — but the thing being measured is a COMPOSITE, and since
s181 the bleed-free corner is not bleed-free: it carries `e = blendEndStop = 0.02418` of clean
signal, which s183 measured reaching **+11.21 dB RE THE OD BRANCH** at this exact null.  A complex
sum of two branches does not track an analytic change in one of them, so AP's own AP5 trade table
is a MODEL of the candidate and not a measurement of it.

⭐ THE TRICK THAT MAKES A RENDERED CHECK FREE (s184's, s195's pattern): `kNotchMixK` is a
`static constexpr` table and is NOT `--fit` exposed, but `FitParams::odNotchDepthDb` adds a
UNIFORM dB to the same `cutDb`, and every render is ONE (grunt, drive, cleanFrac) cell.  So

    odNotchDepthDb = SHIPPED_DEPTH_DB + dK * S(cf)

reproduces `K -> K + dK` at that cell EXACTLY, with no `src/` change, no rebuild, and therefore
no render-cache bill (`build.md`; a relink invalidates every cache in the project).

⛔ THE THREE RULES THIS GATE IS BOUND BY, each already paid for once:
  * grade in DEPTH, never in GAIN, at a mixed setting — the depth->gain inverse is ill-conditioned
    there (s192: slope 0.88 at recovered trips vs 0.061 at missed ones, a 14x separation);
  * print BOTH the point and the area depth (s152) — they are different quantities, and at this
    stage's bleed-free cells they have disagreed about the SIGN (s186's BO5);
  * a refusal is not a reading (s151) — cells the reader refuses are NAMED, never dropped silently.

⚠⚠ WHAT THIS GATE CANNOT SEE, AND IT IS THE DECISION-RELEVANT LIMIT.  `kNotchMixK` multiplies
`S(cf)` at EVERY clean fraction, and the capture matrix has NO cell between cf 0.0242 and 0.2284
on the GRUNT-cut row and NONE AT ALL between 0.0242 and 0.4811 at flat/boost.  S dips to -0.525 at
cf 0.210, so a large negative dK ADDS several dB of cut in a band a player can dial and no capture
can grade.  That is s185's CAPTURED-vs-DIALLABLE split exactly, and BT4 reports it rather than
letting the silence read as a pass.

    python3.11 analysis/mix_corner_gate.py                 # corner + mixed price, rendered
    python3.11 analysis/mix_corner_gate.py --arm flatboost # the GRUNT-keyed variant
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A              # noqa: E402
import captures as C             # noqa: E402
import feature_locus_gate as W   # noqa: E402
import od_tone_restore_fit as F  # noqa: E402

REN_DIR = "build/s196_mix_corner"

#: The three realistic stimulus rungs, imported in spirit from GATE AP's REAL.
REAL = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

#: s151's own converged residual: the bar every acceptance on this stage is quoted against.
FIT_RESIDUAL_DB = 0.83

#: GATE AP's area-solved corner cut, s196 run (`analysis/reports/s196_ap_bleedfree.json`).
#: ⛔ Transcribed here ONLY as a fallback; `--ap-json` re-reads it from the report so this cannot
#: rot the way a transcribed number does (s189's rule about epoch-named literals).
AP_AREA_FALLBACK = {
    ("cut",   0.00): -7.41, ("cut",   0.50):  -1.38, ("cut",   1.00): 16.89,
    ("flat",  0.00): 12.40, ("flat",  0.50):  18.87, ("flat",  1.00): 23.03,
    ("boost", 0.00):  7.38, ("boost", 0.50):  10.79, ("boost", 1.00):  8.16,
}

GI = {"cut": 0, "flat": 1, "boost": 2}
NAME_OF_GI = {v: k for k, v in GI.items()}

FAIL = []


def fail(tag, msg):
    FAIL.append(tag)
    print(f"  ❌ {tag}: {msg}")


def grunt_pos(fname):
    """Physical GRUNT position of a capture.

    ⚠ APVTS order is {Boost, Cut, Flat}; the TABLE's row order is the enum's {Cut, Flat, Boost}.
    Reading `gruntIdx` raw silently permutes the rows — the s151 trap, which cost a whole session
    and is the reason this is a named function rather than an inline index."""
    return NAME_OF_GI[{1: 0, 2: 1, 0: 2}[int(C.parse_capture(fname)["gruntIdx"])]]


def snap_drive(d):
    return min((0.0, 0.5, 1.0), key=lambda x: abs(x - d))


def shipped_depth_db():
    """`FitParams::odNotchDepthDb`, parsed — never transcribed (s174's stale-mirror trap)."""
    import re
    src = open(os.path.join(os.path.dirname(F.HDR), "FitParams.h")).read()
    m = re.search(r"double\s+odNotchDepthDb\s*=\s*([-\d.eE+]+)\s*;", src)
    if not m:
        sys.exit("GATE BT: cannot parse odNotchDepthDb out of FitParams.h — if the name changed, "
                 "update THIS parser rather than letting it fall back to a literal")
    return float(m.group(1))


# ================================================================================================
# rendering
# ================================================================================================
def arm_path(fname, extra):
    """Cache path for one (capture, render-args) pair.

    ⚠ It must be INJECTIVE in what actually varies, or two candidates collide on one file and each
    re-renders over the other — wasteful at best, and at worst it mis-pairs one arm's rows against
    another's numbers (s185 hit exactly that with an `int(x*100)` tag).  `extra` is the only thing
    that varies here, so `extra` is what names the directory; `W.render`'s own argv stamp is the
    second line of defence if that ever stops being true."""
    key = "ship" if not extra else "cand_" + "".join(extra).replace("--fit", "").replace("=", "_")
    return os.path.join(REN_DIR, key.replace(" ", ""), fname.replace(".wav", "") + "_plugin.wav")


def curves_arm(fname, sweep, extra, tag, orig, ref):
    """`od_tone_restore_fit.curves`, but with extra render args and a per-arm cache path.

    Kept byte-for-byte identical to F.curves in its READ path (same align, same transfer_h1, same
    W.smooth, same 100 Hz-8 kHz shape normalisation) so every number here is comparable with every
    stored GATE AP / AQ / AR number.  Only the render args and the output path differ."""
    out = arm_path(fname, extra)
    W.render(out, C.render_args(C.parse_capture(fname), extra_args=extra))

    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)

    def one(al):
        f, m = A.transfer_h1(A.seg_of(al, sweep), ref)
        d = W.smooth(f, m)
        n = (W.GRID >= F.NORM_LO) & (W.GRID <= F.NORM_HI)
        return d - float(np.mean(d[n]))

    return W.GRID, one(cap_al), one(ren_al), out


# ================================================================================================
# BT0 — known answers
# ================================================================================================
def bt0(T, dK, dep0):
    print("\nBT0  KNOWN ANSWERS")
    ok = True

    # (a) the law arithmetic reproduces GATE AP's own SHIPPED corner column.
    corner = T["kMixCf"][0]
    worst = 0.0
    for (g, d), _ in sorted(dK.items()):
        mine = F.cut_db(T, GI[g], d, clean_frac=corner)
        want = F.lerp5(T["kNotchGainDb"][GI[g]], d, T["kX"]) + \
            F.lerp5(T["kNotchMixK"][GI[g]], d, T["kX"]) * T["kMixS"][0]
        worst = max(worst, abs(mine - want))
    print(f"  BT0a  cut_db(corner) == base + kMixS[0]*K            worst |Δ| {worst:.2e} dB")
    if worst > 1e-9:
        fail("BT0a", "the single resolver and the law's own algebra disagree")
        ok = False

    # (b) S is pinned at the reference — what makes a K change safe at the listening condition.
    # ⚠ NOT asserted as an EXACT zero: the node sits at cf 0.440 and kMixCfRef at 0.441, so S there
    # is 1.4e-4.  A bar of "exactly 0" is a tolerance a correct implementation cannot meet
    # (`measurement-discipline.md` §2); the claim that matters is that the induced move is
    # negligible against the bar this stage is judged by, so THAT is what is gated.
    s_ref = F.mix_shape(T["kMixCfRef"], T)
    s_lis = F.mix_shape(0.48114, T)
    mx = max(abs(v) for v in dK.values()) if dK else 0.0
    print(f"  BT0b  S(kMixCfRef={T['kMixCfRef']:.3f}) = {s_ref:+.6f}  (node at cf "
          f"{T['kMixCf'][3]:.3f} ⇒ NOT exactly 0, and that is by construction)")
    print(f"        S(listening 0.48114)  = {s_lis:+.6f};  at max|ΔK| = {mx:.2f} the listening "
          f"cut moves {abs(s_lis)*mx:.3f} dB")
    if abs(s_lis) * mx > FIT_RESIDUAL_DB:
        fail("BT0b", "a K change of this size is NOT decoupled from the listening condition")
        ok = False

    # (c) the emulation identity: odNotchDepthDb is a UNIFORM addend on the same cutDb, so
    #     dep0 + dK*S(cf) reproduces K -> K+dK at that cell.  Asserted on the resolver.
    worst_e = 0.0
    for (g, d), dk in sorted(dK.items()):
        for cf in (corner, 0.2284, 0.48114):
            Tm = {**T, "kNotchMixK": [list(r) for r in T["kNotchMixK"]]}
            Tm["kNotchMixK"][GI[g]] = [v + dk for v in Tm["kNotchMixK"][GI[g]]]
            direct = F.cut_db(Tm, GI[g], d, clean_frac=cf)
            emulated = F.cut_db(T, GI[g], d, clean_frac=cf) + dk * F.mix_shape(cf, T)
            worst_e = max(worst_e, abs(direct - emulated))
    print(f"  BT0c  depthOffset emulation == a real K change        worst |Δ| {worst_e:.2e} dB")
    if worst_e > 1e-9:
        fail("BT0c", "the odNotchDepthDb emulation is NOT identical to changing K")
        ok = False
    print(f"        ⇒ every rendered arm below is a faithful stand-in for the table edit, and the "
          f"shipped depth offset it is added to is {dep0:.3f} dB (parsed, not transcribed)")

    # (d) TWO-SIDED SCOPE, RENDERED.  At cleanFrac = 1 the OD branch is out of the sum entirely, so
    #     no change to a stage INSIDE that branch can reach the output.  A candidate that moves such
    #     a capture is reaching somewhere it must not; one that leaves every OTHER capture unmoved
    #     is inert.  Both directions are asserted — an equality-only guard cannot detect a broken
    #     comparison (s183).
    import hashlib
    pure_clean = [(gn, f, d) for gn in F.SET_META for f, d in F.SETS[gn]
                  if F.clean_frac_of(f) >= 1.0 - 1e-9]
    if not pure_clean:
        print("  BT0d  ⚠ no cleanFrac = 1 capture in SETS — the OD-out-of-circuit control cannot "
              "run;\n        this is a MEMBERSHIP fact, not a pass.")
    else:
        bad = []
        for gn, fname, drv in pure_clean:
            key = (grunt_pos(fname), snap_drive(drv))
            if key not in dK:
                continue
            off = dep0 + dK[key] * F.mix_shape(F.clean_frac_of(fname), T)
            h = {}
            for tag, extra in (("ship", []), ("cand", ["--fit", f"odNotchDepthDb={off:.6f}"])):
                pth = arm_path(fname, extra)
                W.render(pth, C.render_args(C.parse_capture(fname), extra_args=extra))
                h[tag] = hashlib.md5(open(pth, "rb").read()).hexdigest()
            if h["ship"] != h["cand"]:
                bad.append(fname)
        print(f"  BT0d  OD out of circuit (cleanFrac = 1): {len(pure_clean)} capture(s), "
              f"{len(bad)} moved")
        if bad:
            fail("BT0d", f"the candidate reaches a capture with NO OD path: {bad[:3]}")
            ok = False
        else:
            print("        ✅ bit-identical — the change is confined to the OD branch, rendered.")
    return ok


# ================================================================================================
# BT1 — the candidate
# ================================================================================================
def build_candidate(T, ap_area, arm):
    """K_new = (area-solved corner cut - base) / S(corner);  ΔK = K_new - K_shipped."""
    corner_S = T["kMixS"][0]
    dK, rows = {}, []
    for (g, d), area in sorted(ap_area.items()):
        b = F.lerp5(T["kNotchGainDb"][GI[g]], d, T["kX"])
        k_ship = F.lerp5(T["kNotchMixK"][GI[g]], d, T["kX"])
        k_new = (area - b) / corner_S
        if arm == "flatboost" and g == "cut":
            k_new = k_ship                      # leave the Cut row exactly as shipped
        dK[(g, d)] = k_new - k_ship
        rows.append((g, d, b, k_ship, k_new))
    print("\nBT1  THE CANDIDATE — kNotchMixK re-derived from GATE AP's AREA-solved corner cut")
    print(f"  arm: {arm}" + ("   (Cut row held at its shipped value)" if arm == "flatboost" else ""))
    print(f"\n  {'grunt':<6} {'drv':>4} {'base':>8} {'K ship':>8} {'K new':>8} {'ΔK':>8} "
          f"{'Δcut@corner':>12}")
    for g, d, b, ks, kn in rows:
        print(f"  {g:<6} {d:4.2f} {b:8.2f} {ks:8.2f} {kn:8.2f} {kn-ks:+8.2f} "
              f"{(kn-ks)*corner_S:+12.2f}")
    allk = [r[4] for r in rows]
    print(f"\n  ⭐ every K_new is NEGATIVE: {min(allk):.2f} .. {max(allk):.2f} (mean "
          f"{np.mean(allk):.2f}); shipped K spans "
          f"{min(v for r in T['kNotchMixK'] for v in r):.2f} .. "
          f"{max(v for r in T['kNotchMixK'] for v in r):.2f}")
    print("     ⇒ Flat and Boost's shipped K are WRONG-SIGNED against this solve: they say the")
    print("       corner needs MORE cut than the listening mix, and the solve says LESS, as the")
    print("       Cut row already does.  A mix DILUTION is a property of the mix, not of GRUNT.")
    return dK


# ================================================================================================
# BT2 / BT3 — the rendered price
# ================================================================================================
def evaluate(cells, T, dK, dep0, orig, ref, title):
    """Render ship vs candidate at each cell and read the composite null both ways."""
    print(f"\n{title}")
    print(f"  {'group':<15}{'cf':>8}{'grunt':>6}{'drv':>5} | {'point err':>19} | "
          f"{'area err':>19} | moved")
    print(f"  {'':<15}{'':>8}{'':>6}{'':>5} | {'ship':>6}{'cand':>6}{'Δ|e|':>7} | "
          f"{'ship':>6}{'cand':>6}{'Δ|e|':>7} |")
    out = []
    refusals = []
    for gname, fname, drv, cf in cells:
        gp = grunt_pos(fname)
        key = (gp, snap_drive(drv))
        if key not in dK:
            continue
        d_cut = dK[key] * F.mix_shape(cf, T)
        arms = {"ship": [], "cand": ["--fit", f"odNotchDepthDb={dep0 + d_cut:.6f}"]}
        errs = {f"{a}_{m}": [] for a in arms for m in ("pt", "ar")}
        moved = None
        for sw in REAL:
            geo, path = {}, {}
            for a, extra in arms.items():
                g, ped, mod, p = curves_arm(fname, sw, extra, a, orig, ref)
                path[a] = p
                try:
                    geo[a] = F.notch_geometry(g, mod)
                except RuntimeError as e:
                    refusals.append(f"{gname}/{fname}/{sw}/{a}: {e}")
                    geo[a] = None
            try:
                pg = F.notch_geometry(g, ped)
            except RuntimeError as e:
                refusals.append(f"{gname}/{fname}/{sw}/PEDAL: {e}")
                continue
            if moved is None:
                import hashlib
                h = {a: hashlib.md5(open(path[a], "rb").read()).hexdigest() for a in arms}
                moved = h["ship"] != h["cand"]
            for a in arms:
                if geo[a] is None:
                    continue
                errs[f"{a}_pt"].append(pg["depth_point"] - geo[a]["depth_point"])
                errs[f"{a}_ar"].append(pg["depth_area"] - geo[a]["depth_area"])
        m = {k: (float(np.mean(np.abs(v))) if v else float("nan")) for k, v in errs.items()}
        out.append((gname, fname, gp, drv, cf, d_cut, m, moved))
        print(f"  {gname:<15}{cf:8.4f}{gp:>6}{drv:5.2f} | {m['ship_pt']:6.2f}{m['cand_pt']:6.2f}"
              f"{m['cand_pt']-m['ship_pt']:+7.2f} | {m['ship_ar']:6.2f}{m['cand_ar']:6.2f}"
              f"{m['cand_ar']-m['ship_ar']:+7.2f} | "
              f"{'yes' if moved else 'BIT-IDENT'}  (Δcut {d_cut:+.2f})")
    if refusals:
        print(f"\n  ⚠ {len(refusals)} reader REFUSAL(s) — NAMED, not dropped silently (s151):")
        for r in refusals[:8]:
            print(f"      {r}")
        if len(refusals) > 8:
            print(f"      ... and {len(refusals) - 8} more")
    return out, refusals


def summarise(rows, label):
    pt_s = [r[6]["ship_pt"] for r in rows if not np.isnan(r[6]["ship_pt"])]
    pt_c = [r[6]["cand_pt"] for r in rows if not np.isnan(r[6]["cand_pt"])]
    ar_s = [r[6]["ship_ar"] for r in rows if not np.isnan(r[6]["ship_ar"])]
    ar_c = [r[6]["cand_ar"] for r in rows if not np.isnan(r[6]["cand_ar"])]
    if not pt_s:
        print(f"  {label}: no readable cells")
        return None
    print(f"\n  {label} POOLED mean|err|:  POINT {np.mean(pt_s):5.2f} -> {np.mean(pt_c):5.2f} "
          f"({np.mean(pt_c)-np.mean(pt_s):+5.2f})   AREA {np.mean(ar_s):5.2f} -> "
          f"{np.mean(ar_c):5.2f} ({np.mean(ar_c)-np.mean(ar_s):+5.2f})")
    return {"pt_ship": float(np.mean(pt_s)), "pt_cand": float(np.mean(pt_c)),
            "ar_ship": float(np.mean(ar_s)), "ar_cand": float(np.mean(ar_c))}


# ================================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--arm", choices=("all", "flatboost"), default="all",
                    help="`all` re-fits every GRUNT row's K; `flatboost` holds the Cut row at its "
                         "shipped value (the s187/s195 pattern: key only where the defect is)")
    ap.add_argument("--ap-json", default="analysis/reports/s196_ap_bleedfree.json",
                    help="GATE AP report to take the AREA-solved corner cut from")
    ap.add_argument("--min-dcut", type=float, default=0.15,
                    help="mixed cells whose |Δcut| is below this are rendered as INERTNESS "
                         "controls only (a handful), not as price")
    a = ap.parse_args()

    print("=" * 100)
    print("GATE BT — OdToneRestore's mix law at the bleed-free corner, priced by RENDER")
    print("=" * 100)

    T = F.shipped_tables()
    dep0 = shipped_depth_db()
    corner = T["kMixCf"][0]

    # ---- the target, imported rather than transcribed where possible --------------------------
    ap_area, src = dict(AP_AREA_FALLBACK), "TRANSCRIBED FALLBACK"
    if os.path.exists(a.ap_json):
        import json
        tbl = json.load(open(a.ap_json)).get("table", {})
        got = {}
        for key, rec in tbl.items():                       # keys look like "Boost_0.50"
            gname, _, dtxt = key.rpartition("_")
            if gname.lower() in GI and rec.get("solve_area") is not None:
                got[(gname.lower(), float(dtxt))] = float(rec["solve_area"])
        if set(got) == set(AP_AREA_FALLBACK):
            ap_area, src = got, a.ap_json
        elif got:
            print(f"  ⚠ {a.ap_json} covers {len(got)} of {len(AP_AREA_FALLBACK)} cells — "
                  f"membership differs from the fallback, so the fallback is kept and the report "
                  f"is NOT silently merged (a partial read is a malformed input, s129).")
    print(f"  AREA-solved corner cut taken from: {src}")
    if src == "TRANSCRIBED FALLBACK":
        print("  ⚠ these are TRANSCRIBED s196 values. A transcribed number rots on its own "
              "(s189);\n    re-run GATE AP and pass --ap-json so this reads the report instead.")
    else:
        worst_t = max(abs(ap_area[k] - AP_AREA_FALLBACK[k]) for k in ap_area)
        print(f"  ⭐ free cross-check: the parsed values agree with the transcribed fallback to "
              f"{worst_t:.3f} dB\n     (they should, on this epoch — a large Δ means the report "
              f"moved and the fallback is stale).")

    dK = build_candidate(T, ap_area, a.arm)
    if not bt0(T, dK, dep0):
        print("\n❌ a known answer failed — nothing below is readable.")
        return 1

    orig, ref = W._load_orig()

    # ---- BT2: the corner ------------------------------------------------------------------------
    corner_cells = []
    for sname in ("bleedfree", "grunt_flat", "grunt_boost"):
        for fname, drv in F.SETS[sname]:
            corner_cells.append((sname, fname, drv, F.clean_frac_of(fname)))
    rows_c, ref_c = evaluate(corner_cells, T, dK, dep0, orig, ref,
                             "BT2  THE CORNER (cf = %.5f) — rendered, not analytic" % corner)
    sum_c = summarise(rows_c, "BT2 CORNER")

    # ---- BT3: every captured MIXED cell the candidate moves -------------------------------------
    seen, mixed_cells, inert = set(), [], []
    for gname in sorted(F.SET_META):
        for fname, drv in F.SETS[gname]:
            cf = F.clean_frac_of(fname)
            if cf <= corner + 1e-9 or (fname, drv) in seen:
                continue
            key = (grunt_pos(fname), snap_drive(drv))
            if key not in dK:
                continue
            seen.add((fname, drv))
            d = abs(dK[key] * F.mix_shape(cf, T))
            (mixed_cells if d >= a.min_dcut else inert).append((gname, fname, drv, cf))
    print(f"\n  BT3 membership: {len(mixed_cells)} captured mixed cells move by >= "
          f"{a.min_dcut} dB of applied cut; {len(inert)} move less and are sampled as "
          f"INERTNESS controls.")
    rows_m, ref_m = evaluate(mixed_cells, T, dK, dep0, orig, ref,
                             "BT3  THE PRICE AT CAPTURED MIXED CELLS — rendered")
    sum_m = summarise(rows_m, "BT3 MIXED")

    if inert:
        rows_i, _ = evaluate(inert[:6], T, dK, dep0, orig, ref,
                             "BT3b INERTNESS CONTROLS (|Δcut| < %.2f dB) — these must barely move"
                             % a.min_dcut)
        summarise(rows_i, "BT3b INERT")

    # ---- BT4: the band no capture can grade ------------------------------------------------------
    print("\nBT4  ⚠⚠ THE DIALLABLE BAND NO CAPTURE CAN GRADE (s185's CAPTURED-vs-DIALLABLE split)")
    caps = sorted({round(F.clean_frac_of(f), 5)
                   for gn in F.SET_META for f, _ in F.SETS[gn]})
    gaps = {}
    for g in ("cut", "flat", "boost"):
        have = sorted({round(F.clean_frac_of(f), 5)
                       for gn in F.SET_META for f, _ in F.SETS[gn]
                       if grunt_pos(f) == g and F.clean_frac_of(f) > corner + 1e-9})
        gaps[g] = (corner, min(have) if have else None)
    # ⛔ The interval is OPEN at the corner: cf = corner is the cell BT2 measures and fixes, so
    # including it would report the intended correction as if it were ungraded risk — which is the
    # opposite of this sub-gate's job.  Probe strictly inside.
    # Two DIFFERENT risks live in this band and pooling them would hide the second:
    #  (i) the largest excursion anywhere strictly inside it — which sits just above the corner,
    #      because S is continuous there, and is really the corner correction bleeding upward;
    # (ii) the largest excursion where S has the OPPOSITE SIGN to the corner, i.e. where the
    #      candidate ADDS cut instead of removing it.  That one is qualitatively new behaviour,
    #      not a continuation of the fix, and it is the one a reader would not predict.
    print(f"  {'grunt':<6} {'ungraded cf band':<22} {'worst Δcut inside':>19} "
          f"{'worst where S flips sign':>28}")
    opp = []
    for g, (lo, hi) in gaps.items():
        if hi is None:
            print(f"  {g:<6} {'no mixed capture at all':<22} {'-':>19} {'-':>28}")
            continue
        probe = np.linspace(lo, hi, 801)[1:-1]           # OPEN interval
        worst, at, wflip, atflip = 0.0, None, 0.0, None
        for cf in probe:
            s = F.mix_shape(float(cf), T)
            for d in (0.0, 0.5, 1.0):
                v = dK[(g, d)] * s
                if abs(v) > abs(worst):
                    worst, at = v, float(cf)
                if s < 0.0 and abs(v) > abs(wflip):      # S(corner) > 0, so S < 0 is the flip
                    wflip, atflip = v, float(cf)
        # ΔK is exactly 0 for a row this arm holds at its shipped value, so there IS no excursion
        # to report and `at`/`atflip` stay None.  That is a real outcome of the arm, not a missing
        # reading — print it as such rather than formatting a None (which is how it crashed once).
        wt = f"{worst:+8.2f} dB @ cf {at:.3f}" if at is not None else "unchanged by this arm"
        fl = f"{wflip:+8.2f} dB @ cf {atflip:.3f}" if atflip is not None else "unchanged"
        print(f"  {g:<6} ({lo:.4f}, {hi:.4f}){'':<6} {wt:>21} {fl:>28}")
        if at is not None and atflip is not None:
            opp.append(worst * wflip < 0.0)
    print("  ⇒ settings a player can dial and NO capture can grade. Reported, never quoted as a")
    print("    pass — 'no capture moved' is a statement about the GRID, not about the law (s185).")
    # ⭐ COMPUTED, not narrated: the whole reason column 3 exists is that it is the OPPOSITE
    # sign to column 2 — that is what makes it qualitatively new behaviour rather than the corner
    # correction bleeding upward.  If the two columns ever share a sign, the split has stopped
    # separating anything and saying otherwise would be narration.
    if opp and all(opp):
        print(f"  ⇒ COMPUTED: column 3 is OPPOSITE-SIGNED to column 2 at {sum(opp)}/{len(opp)} "
              f"rows ⇒ it is a genuinely different behaviour, not the corner fix bleeding upward.")
        print("    That is the decision-relevant column: it is where the candidate ADDS cut, and")
        print("    nothing on disk can check it.")
    else:
        print(f"  ⇒ COMPUTED: column 3 is opposite-signed at only {sum(opp)}/{len(opp)} rows ⇒ the "
              f"split is NOT separating two behaviours here and column 3 supports nothing.")

    # ---- verdict --------------------------------------------------------------------------------
    print("\n" + "=" * 100)
    print("VERDICT")
    print("=" * 100)
    if FAIL:
        print(f"  ❌ {len(FAIL)} known answer(s) failed: {FAIL}")
        return 1
    if sum_c:
        dpt, dar = sum_c["pt_cand"] - sum_c["pt_ship"], sum_c["ar_cand"] - sum_c["ar_ship"]
        print(f"  CORNER : point {sum_c['pt_ship']:.2f} -> {sum_c['pt_cand']:.2f} ({dpt:+.2f}), "
              f"area {sum_c['ar_ship']:.2f} -> {sum_c['ar_cand']:.2f} ({dar:+.2f})")
    if sum_m:
        mpt, mar = sum_m["pt_cand"] - sum_m["pt_ship"], sum_m["ar_cand"] - sum_m["ar_ship"]
        print(f"  MIXED  : point {sum_m['pt_ship']:.2f} -> {sum_m['pt_cand']:.2f} ({mpt:+.2f}), "
              f"area {sum_m['ar_ship']:.2f} -> {sum_m['ar_cand']:.2f} ({mar:+.2f})")
    # ---- BT5: a sign-coherence argument the stage's OWN header already contains ------------------
    print("\nBT5  SIGN COHERENCE — computed from the stage's own documented physics, no data needed")
    ship_k = {(g, d): F.lerp5(T["kNotchMixK"][GI[g]], d, T["kX"])
              for (g, d) in dK}
    new_k = {k: ship_k[k] + v for k, v in dK.items()}
    n_ship_pos = sum(1 for v in ship_k.values() if v > 0)
    n_new_pos = sum(1 for v in new_k.values() if v > 0)
    print(f"  cells with POSITIVE kNotchMixK:  shipped {n_ship_pos}/{len(ship_k)}   "
          f"candidate {n_new_pos}/{len(new_k)}")
    print("  `OdToneRestore.h` states the shape's own physics: S rises to +0.951 at the corner")
    print("  after dipping to -0.525 at cf ~ 0.21, and *with K NEGATIVE* that makes the required")
    print("  cut PEAK at intermediate mix and fall toward bleed-free.  s156's CLOSED/REFUTED row")
    print("  gives the mechanism: at intermediate mix the model's own null is diluted hardest")
    print("  while the pedal's target is still deep; at cf -> 0 the model's null is already close.")
    print("  ⭐⭐ THAT MECHANISM IS A PROPERTY OF THE MIX, SO IT CANNOT DEPEND ON THE GRUNT SWITCH")
    print("     — yet the shipped table applies the SAME S with POSITIVE K at flat/boost, which")
    print("     INVERTS the hump there: it makes the required cut DIP at intermediate mix and PEAK")
    print("     at the corner, contradicting the stage's own stated physics at 2 of 3 positions.")
    if n_new_pos == 0 and n_ship_pos > 0:
        print(f"  ⇒ COMPUTED: the candidate restores a single sign orientation across all three")
        print(f"    GRUNT rows ({n_ship_pos} sign contradictions -> 0).  This is corroboration from")
        print(f"    a direction with no fit, no threshold and no reference in it.")
    else:
        print(f"  ⇒ COMPUTED: the candidate does NOT resolve the sign contradiction "
              f"({n_ship_pos} -> {n_new_pos}); BT5 supports nothing.")

    # ---- BT6: what s153's decision could NOT have known -----------------------------------------
    print("\nBT6  ⚠⚠ s153's METRIC DECISION RESTS ON A TRADE THAT NO LONGER HOLDS")
    print("  s153 chose the POINT metric for this table as a USER DECISION, on three grounds, and")
    print("  its FIRST ground was that the trade is a WASH: 'entries move up to 4.92 dB while")
    print("  achieved error moves ~0.5 dB ⇒ the constant is weakly identified'.")
    if os.path.exists(a.ap_json):
        import json
        rep = json.load(open(a.ap_json))
        tr, cen, rd = rep.get("trade", {}), rep.get("censored"), rep.get("readings")
        if tr:
            s153 = {"ship_pt": 4.03, "ship_ar": 2.06, "area_pt": 4.54, "area_ar": 1.54}
            print(f"\n  {'':<19}{'point err':>22}{'area err':>22}")
            print(f"  {'':<19}{'shipped':>10}{'area-solved':>12}"
                  f"{'shipped':>10}{'area-solved':>12}")
            print(f"  {'s153 (as decided)':<19}{s153['ship_pt']:10.2f}{s153['area_pt']:12.2f}"
                  f"{s153['ship_ar']:10.2f}{s153['area_ar']:12.2f}")
            print(f"  {'TODAY':<19}{tr['ship_pt']:10.2f}{tr['area_pt']:12.2f}"
                  f"{tr['ship_ar']:10.2f}{tr['area_ar']:12.2f}")
            cost_then = s153["area_pt"] - s153["ship_pt"]
            buy_then = s153["ship_ar"] - s153["area_ar"]
            cost_now = tr["area_pt"] - tr["ship_pt"]
            buy_now = tr["ship_ar"] - tr["area_ar"]
            print(f"\n  s153 : the area solve COST {cost_then:+.2f} dB of point accuracy to BUY "
                  f"{buy_then:+.2f} dB of area  ⇒ a wash")
            print(f"  TODAY: it COSTS {cost_now:+.2f} dB to BUY {buy_now:+.2f} dB"
                  f"  ⇒ {'NOT a wash' if abs(cost_now) < 0.5 * abs(buy_now) else 'still a trade'}")
            print("  ⛔ s153's numbers are NOT re-derivable here (different epoch, 8 shipped")
            print("     constants since), so the CHANGE is not attributable to any one of them.")
            print("     What is quotable is that the ground the decision was taken on no longer")
            print("     describes the choice.")
        if cen and rd:
            print(f"\n  ⭐ AND TWO FINDINGS POSTDATE s153 THAT BEAR ON *WHICH ESTIMATOR IS READABLE*:")
            print(f"     · GATE AP's own census, this run: {cen} of {rd} pedal depth readings on")
            print(f"       this membership are CENSORED by the deconvolution residue, so their")
            print(f"       POINT depth is a LOWER BOUND. (s186's BO5 sharpened it: bleed-free the")
            print(f"       two estimators disagree about the SIGN at 4 of 6 flat/boost cells, the")
            print(f"       censored and uncensored populations separating by a 6.02 dB gap.)")
            print(f"     · s191's AP1b: at a MIXED setting the censoring robustness is 1.0x, i.e.")
            print(f"       the two metrics measure the same thing there and the choice does not")
            print(f"       exist. ⇒ THE METRIC CHOICE ONLY BITES AT THE CORNER — and the corner is")
            print(f"       exactly where the POINT reading is the censored one.")
            print(f"  ⚠ NOT the same claim as AP6, and do not merge them: AP6 measures that the")
            print(f"    SIZE of the point-vs-area gap does not track the censoring (r = +0.43) and")
            print(f"    attributes it to SHAPE mismatch. That is about the gap's magnitude; this is")
            print(f"    about which of the two readings is a BOUND. Both hold.")
    print("\n  ⇒ WHICH METRIC THE EAR FOLLOWS IS STILL ESTABLISHED BY NOTHING. This gate reports")
    print("    both columns and adjudicates neither — but s153's stated ground is measurably gone,")
    print("    so treating that decision as settled is no longer supported. USER DECISION.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
