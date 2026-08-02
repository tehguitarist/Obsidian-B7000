#!/usr/bin/env python3.11
"""GATE J -- localise what is LEFT of the OD error, so the next fix has a target.

Session 102.  No render: every number here is a re-read of a report already on disk.

WHY THIS EXISTS
---------------
GATE I (session 101, `hf_artefact_gate.py`) established that the OD 8-16.3 kHz region is
dominated by ND's own drive-generated artefact and is NOT ours to fix -- the pedal's rolloff
RATE over that octave is drive-dependent and turns positive, which no linear filter can do.
Its actionable conclusion was "stop aiming model work at 8-16.3 kHz", and it measured that the
remaining OD error is genuinely broadband (p99 is still 10.28 with all four HF bands dropped).

It did NOT say WHERE that broadband remainder lives.  Eight gate rows are over SHIP and the
project has no localisation of them by condition -- so the next fix would be chosen by
narrative, not by measurement.  This tool decomposes the residual three ways:

    per BAND       which bands carry it (HF included AND excluded, side by side)
    per CONDITION  which knob settings carry it (marginals over blend/level/drive/switches)
    per BLEED      the A3 discriminator -- does the midband error track clean-bleed exposure?

The third is the one with a pre-registered consequence.  Open-work item 5 (A3) is a ~5-7 dB
OD-vs-bleed imbalance over 100-400 Hz, corroborated by two instruments (sessions 85/86), and it
is authorised as ONE timeboxed session.  If the residual concentrates at 100-400 Hz on rows
where the clean bleed is small, that authorises spending it.  If it does not, that session is
saved -- which is the cheaper outcome and the reason to measure before spending.

WHAT IS AND IS NOT DECOMPOSABLE  (read before quoting a "share")
---------------------------------------------------------------
The gated headline is `band-RMS` = mean over ROWS of sqrt(mean over BANDS of d^2).  A mean of
square roots does not decompose into per-band shares -- there is no honest way to say "band X is
N% of 2.409".  The pooled MEAN SQUARE does decompose, exactly:

    pooled_ms = mean over all (row, band) cells of d^2      = sum_b w_b * ms_b

so this tool reports per-band shares of `pooled_ms` and prints `pooled_rms = sqrt(pooled_ms)`
BESIDE the headline band-RMS, labelled as a different statistic.  They are not equal and are not
interchangeable; J1 checks the decomposition against the pooled figure, never against the
headline.  (`difference-statistics-hide-common-mode`, applied to an aggregate rather than a
difference.)

GATES (all computed, exits non-zero on failure)
-----------------------------------------------
J1  known answer -- the per-band decomposition recombines to the pooled statistics, and this
    tool's own OD/CLEAN row counts and region statistics reproduce `release_gate.py`'s to 1e-9.
    It IMPORTS release_gate's `deltas`/`subsets`/`region_sel` rather than re-implementing them,
    so a divergence means a real bug here, not two drifting copies.
J2  mutation -- dropping one band must BREAK J1's recombination.  Without this, J1 passes
    vacuously for any decomposition that happens to sum to the right total (`empty-gate-must-fail`).
J3  the sub-band partition of 100 Hz-8 kHz tiles it exactly (8 + 5 + 6 bands), asserted the same
    way `release_gate.check_clean_partition` does -- a silently dropped sub-band would improve
    every midband figure at once.

Run:
    python3.11 analysis/od_residual_localise.py analysis/reports/s99_attack_cand.json
    python3.11 analysis/od_residual_localise.py REPORT.json --json analysis/reports/s102_localise.json
"""
import argparse
import json
import sys

import numpy as np

import matrix_grade as MG
import release_gate as RG

# The midband sub-partition.  100 Hz-8 kHz is the widest failing OD row (median 0.568 / p90 4.458)
# and spans 6 octaves, so "the midband is bad" is not a target.  A3's own region is 100-400 Hz --
# cut on the real line so the tiling is by construction, exactly as G_SUBS is in
# attack_shape_screen.  J3 asserts these tile the parent region.
MID_SUBS = (
    ("100-400 Hz", 100.0, 400.0),      # A3 / GAP #3b territory
    ("400-1600 Hz", 400.0, 1600.0),
    ("1.6-8 kHz", 1600.0, 8000.0),
)
MID_PARENT = "100 Hz-8 kHz"

# The knob axes to take marginals over.  Read from each capture's stored `settings`, NOT parsed
# from the filename -- `measurement-condition-needs-its-own-gate` (s65): a filename token is a
# claim about the render, the settings dict is what the render was actually given.
AXES = ("blend", "level", "drive", "attackIdx", "gruntIdx")

TOL = 1e-9


def sub_idx(bands, idx, lo, hi):
    """Positions WITHIN `idx` (the graded band list) for a half-open [lo, hi) range."""
    return [j for j, i in enumerate(idx) if lo <= bands[i] < hi]


def check_mid_partition(bands, idx):
    """J3 -- MID_SUBS must tile MID_PARENT exactly."""
    parent = set(RG.region_sel(bands, idx, MID_PARENT))
    covered, seen = 0, set()
    for _, lo, hi in MID_SUBS:
        s = set(sub_idx(bands, idx, lo, hi))
        if s & seen:
            sys.exit(f"GATE J3 FAIL: sub-bands overlap at {sorted(s & seen)}")
        seen |= s
        covered += len(s)
    if seen != parent:
        sys.exit(f"GATE J3 FAIL: sub-bands cover {covered} of {len(parent)} bands in "
                 f"{MID_PARENT} (missing {sorted(parent - seen)}, extra {sorted(seen - parent)})")
    print(f"  J3 OK   MID_SUBS tile {MID_PARENT} exactly: "
          f"{' + '.join(str(len(sub_idx(bands, idx, lo, hi))) for _, lo, hi in MID_SUBS)}"
          f" = {len(parent)} bands")


def signed_deltas(path, idx, method=None):
    """-> {(file, sweep): signed (plugin - pedal) per graded band}.

    ⚠ `release_gate.deltas` returns |delta|, which is right for every magnitude statistic here
    and WRONG for J11: the mean of |delta| is not an offset, it is just another magnitude, and
    using it silently turns the level/shape split into nonsense.  J12 gates this loader against
    RG's own by requiring |signed| == RG's array elementwise."""
    caps = MG.load(path)[1]
    out = {}
    for f, c in caps.items():
        for sw, fr in c["fr"].items():
            src = fr["methods"][method] if method is not None else fr
            p, q = src["plugin_db"], src["pedal_db"]
            if max(p) < MG.SILENT_DB or max(q) < MG.SILENT_DB:
                continue
            out[(f, sw)] = np.array([p[i] - q[i] for i in idx])
    return out


def stack(subset):
    """-> (n_rows, n_bands) array of |delta| for a release_gate subset dict."""
    if not subset:
        sys.exit("GATE J: empty subset -- refusing to summarise nothing (empty-gate-must-fail)")
    return np.vstack([v[0] for v in subset.values()])


def gate_j1_j2(bands, idx, od, drop=None):
    """J1: per-band decomposition must recombine to the pooled mean square.
    J2: with `drop` set, the same check must FAIL."""
    d = stack(od)
    keep = [j for j in range(d.shape[1]) if j != drop] if drop is not None else list(range(d.shape[1]))
    pooled_ms = float(np.mean(d[:, keep] ** 2))
    per_band_ms = np.mean(d ** 2, axis=0)
    # equal band weights, so the recombination is a plain mean over the FULL band list
    recomb = float(np.mean(per_band_ms))
    return pooled_ms, recomb, abs(pooled_ms - recomb)


def region_stats(d, sel):
    v = d[:, sel].ravel()
    return {"n": int(v.size), "median": float(np.median(v)), "p90": float(np.percentile(v, 90)),
            "p99": float(np.percentile(v, 99)), "max": float(np.max(v)),
            "rms": float(np.sqrt(np.mean(v ** 2)))}


def band_rms_headline(d):
    """The GATED statistic: mean over rows of the per-row band-RMS."""
    return float(np.mean(np.sqrt(np.mean(d ** 2, axis=1))))


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--method", default=None, help="re-grade from a stored FR read (csd|h1|h1band)")
    ap.add_argument("--json", help="write the localisation to this path")
    args = ap.parse_args()

    bands, idx, rows, used = RG.deltas(args.report, args.method)
    subs = RG.subsets(rows)
    od = subs["OD"]
    d = stack(od)

    print(f"=== GATE J -- OD residual localisation: {args.report.split('/')[-1]} ===")
    print(f"    FR read: {used}   graded {MG.GRADE_LO:g}-{MG.GRADE_HI:g} Hz   "
          f"OD rows {len(od)} (ex gain-n12), bands {len(idx)}")

    # ---- gates -------------------------------------------------------------------------
    print("\n-- gates --")
    check_mid_partition(bands, idx)

    pooled_ms, recomb, err = gate_j1_j2(bands, idx, od)
    if err > TOL:
        sys.exit(f"GATE J1 FAIL: per-band decomposition recombines to {recomb:.12g}, "
                 f"pooled mean square is {pooled_ms:.12g} (|diff| {err:.3g})")
    print(f"  J1 OK   per-band decomposition recombines to the pooled mean square "
          f"(|diff| {err:.3g})")

    _, _, err_mut = gate_j1_j2(bands, idx, od, drop=0)
    if err_mut <= TOL:
        sys.exit("GATE J2 FAIL: dropping a band did NOT break the recombination -- J1 is vacuous")
    print(f"  J2 OK   dropping one band breaks it (|diff| {err_mut:.3g}), so J1 is not vacuous")

    # reproduce release_gate's own OD region statistics through this code path
    bad = []
    for region, ship_med, ship_p90 in (("25-100 Hz", 0.70, 2.50), (MID_PARENT, 0.50, 2.00),
                                       ("8-16.3 kHz", 0.70, 2.50)):
        s = region_stats(d, RG.region_sel(bands, idx, region))
        pool = np.concatenate([v[0][RG.region_sel(bands, idx, region)] for v in od.values()])
        if abs(float(np.median(pool)) - s["median"]) > TOL:
            bad.append(region)
    if bad:
        sys.exit(f"GATE J1 FAIL: region statistics disagree with the pooled read at {bad}")
    print("  J1 OK   region statistics reproduce release_gate's pooled read")

    headline = band_rms_headline(d)
    print(f"\n  headline band-RMS (GATED, mean of per-row RMS) : {headline:.3f} dB")
    print(f"  pooled RMS        (decomposable, all cells)    : {np.sqrt(pooled_ms):.3f} dB")
    print("  ^ different statistics -- shares below are of the POOLED mean square, never of the "
          "headline.")

    # ---- per band ----------------------------------------------------------------------
    print("\n-- J4: per band --")
    print(f"{'band Hz':>10}{'mean|d|':>10}{'median':>9}{'p90':>9}{'max':>9}"
          f"{'ms share %':>12}{'ex-HF share %':>15}")
    hf = [j for j, i in enumerate(idx) if bands[i] >= 8000.0]
    non_hf = [j for j in range(len(idx)) if j not in hf]
    ms = np.mean(d ** 2, axis=0)
    tot, tot_nohf = ms.sum(), ms[non_hf].sum()
    per_band = {}
    for j, i in enumerate(idx):
        share = 100.0 * ms[j] / tot
        share_nohf = 100.0 * ms[j] / tot_nohf if j in non_hf else float("nan")
        col = d[:, j]
        per_band[bands[i]] = {"mean": float(col.mean()), "median": float(np.median(col)),
                              "p90": float(np.percentile(col, 90)), "max": float(col.max()),
                              "ms_share": share, "ms_share_ex_hf": share_nohf}
        flag = "  <- HF (GATE I: ND's artefact)" if j in hf else ""
        nh = f"{share_nohf:15.1f}" if j in non_hf else f"{'—':>15}"
        print(f"{bands[i]:10.1f}{col.mean():10.2f}{np.median(col):9.2f}"
              f"{np.percentile(col, 90):9.2f}{col.max():9.2f}{share:12.1f}{nh}{flag}")
    print(f"\n  HF (>=8 kHz, 4 bands) carries {100.0 * ms[hf].sum() / tot:.1f}% of the pooled "
          f"mean square.")

    # ---- exclusion consequence, on BOTH statistics --------------------------------------
    # session 91's trap: an exclusion can make a statistic WORSE.  Compute, never assume.
    print("\n-- J5: consequence of dropping the four HF bands (session 91's exclusion trap) --")
    full, ex = region_stats(d, list(range(len(idx)))), region_stats(d, non_hf)
    print(f"{'statistic':<14}{'all bands':>12}{'ex HF':>12}{'move':>10}")
    for k in ("median", "p90", "p99", "max"):
        mv = ex[k] - full[k]
        print(f"{k:<14}{full[k]:12.3f}{ex[k]:12.3f}{mv:+10.3f}"
              f"{'   <- WORSE' if mv > 0 else ''}")
    h_ex = band_rms_headline(d[:, non_hf])
    print(f"{'band-RMS':<14}{headline:12.3f}{h_ex:12.3f}{h_ex - headline:+10.3f}")

    # ---- midband sub-bands --------------------------------------------------------------
    print(f"\n-- J6: inside {MID_PARENT} (the widest failing row) --")
    print(f"{'sub-band':<14}{'bands':>7}{'median':>9}{'p90':>9}{'p99':>9}{'max':>9}{'rms':>9}")
    mid_out = {}
    for name, lo, hi in MID_SUBS:
        sel = sub_idx(bands, idx, lo, hi)
        s = region_stats(d, sel)
        mid_out[name] = s
        print(f"{name:<14}{len(sel):7d}{s['median']:9.3f}{s['p90']:9.3f}"
              f"{s['p99']:9.3f}{s['max']:9.3f}{s['rms']:9.3f}")

    # ---- per condition ------------------------------------------------------------------
    print("\n-- J7: marginals over the knob axes (band-RMS, ex HF) --")
    caps = {c["file"]: c for c in json.load(open(args.report))["captures"]}
    keys = list(od.keys())
    dn = d[:, non_hf]
    axis_out = {}
    for ax in AXES:
        buckets = {}
        for r, k in enumerate(keys):
            st = caps[k[0]]["settings"]
            if ax not in st:
                continue
            buckets.setdefault(st[ax], []).append(r)
        if not buckets:
            continue
        axis_out[ax] = {}
        print(f"\n  {ax}:")
        print(f"{'    value':<12}{'rows':>6}{'band-RMS':>11}{'median':>9}{'p90':>9}")
        for val in sorted(buckets):
            rr = buckets[val]
            sub = dn[rr]
            br = band_rms_headline(sub)
            axis_out[ax][str(val)] = {"rows": len(rr), "band_rms": br,
                                      "median": float(np.median(sub)),
                                      "p90": float(np.percentile(sub, 90))}
            print(f"    {val!s:<8}{len(rr):6d}{br:11.3f}{np.median(sub):9.3f}"
                  f"{np.percentile(sub, 90):9.3f}")

    # ---- the A3 discriminator ------------------------------------------------------------
    # ⛔ CORRECTED SESSION 108.  This block used to read "bleed-free BY TOPOLOGY is blend == 1.0:
    # BLEND crossfades OD<->clean, so at max the output carries no clean path at all, whatever
    # LEVEL does."  ⇒ REFUTED by GATE K2 (session 103), which evaluates the shipped LevelBlend
    # stage instead of quoting its header: the BLEND pot's BODY bridges the LEVEL wiper to the
    # clean source at EVERY blend position, so the bleed vanishes only where the wiper's source
    # impedance is zero -- LEVEL max or LEVEL min.  Inside this "free" set the clean coefficient
    # runs from -0.08 dB re the OD (LEVEL 0.125) to -inf (LEVEL max), ORDERED BY LEVEL, giving
    # r(LEVEL, clean fraction) = -0.961.  So `free` is a LOW-BLEED set, not a bleed-free one, and
    # every statistic conditioned on it is confounded with LEVEL.  J8's split still discriminates
    # (the two sides differ a lot in bleed) but J9's per-axis spreads inherit the confound -- see
    # the session-108 note on the GRUNT item in CLAUDE.md.
    print("\n-- J8: the A3 discriminator -- does the error track clean-bleed exposure? --")
    free = [r for r, k in enumerate(keys) if caps[k[0]]["settings"].get("blend") == 1.0]
    bled = [r for r, k in enumerate(keys) if caps[k[0]]["settings"].get("blend", 1.0) < 1.0]
    if not free or not bled:
        sys.exit("GATE J8 FAIL: one side of the bleed split is empty -- cannot discriminate")
    print(f"{'sub-band':<14}{'bleed-FREE (blend=1)':>22}{'blended (blend<1)':>20}{'ratio':>9}")
    print(f"{'':14}{'n=' + str(len(free)):>22}{'n=' + str(len(bled)):>20}")
    a3_out = {}
    for name, lo, hi in MID_SUBS + (("25-100 Hz", 25.0, 100.0),):
        sel = sub_idx(bands, idx, lo, hi)
        if not sel:
            continue
        f_rms = float(np.sqrt(np.mean(d[np.ix_(free, sel)] ** 2)))
        b_rms = float(np.sqrt(np.mean(d[np.ix_(bled, sel)] ** 2)))
        a3_out[name] = {"free_rms": f_rms, "bled_rms": b_rms, "ratio": f_rms / b_rms}
        print(f"{name:<14}{f_rms:22.3f}{b_rms:20.3f}{f_rms / b_rms:9.2f}")
    print("\n  A ratio >> 1 means the error is concentrated where the OD path is EXPOSED, i.e.")
    print("  it is an OD-path defect that the clean bleed masks -- A3's signature.  A ratio ~1")
    print("  means the defect is shared and A3 is NOT the remaining story.")

    # ---- conditional marginals ------------------------------------------------------------
    # J7's marginals are CONFOUNDED: `blend` spans 0.200 -> 3.120 band-RMS on its own, and the
    # other axes are not balanced across it (e.g. every blend-0 row is also drive 0.5).  So a
    # GRUNT or LEVEL effect read off J7 could be nothing but the blend mix of its rows.  Condition
    # on the dominant axis and re-read: only what survives here is a real second effect.
    print("\n-- J9: the same axes CONDITIONED on bleed-free (blend = 1.0), ex HF --")
    print(f"    n = {len(free)} rows; this removes the confound J7's marginals carry.")
    cond_out = {}
    for ax in AXES:
        if ax == "blend":
            continue
        buckets = {}
        for r in free:
            st = caps[keys[r][0]]["settings"]
            if ax in st:
                buckets.setdefault(st[ax], []).append(r)
        if len(buckets) < 2:
            continue
        cond_out[ax] = {}
        print(f"\n  {ax}:")
        print(f"{'    value':<12}{'rows':>6}{'band-RMS':>11}{'median':>9}{'p90':>9}{'vs best':>10}")
        vals = sorted(buckets)
        brs = {v: band_rms_headline(dn[buckets[v]]) for v in vals}
        best = min(brs.values())
        for v in vals:
            rr = buckets[v]
            sub = dn[rr]
            cond_out[ax][str(v)] = {"rows": len(rr), "band_rms": brs[v]}
            mark = "  <- n<10, weak" if len(rr) < 10 else ""
            print(f"    {v!s:<8}{len(rr):6d}{brs[v]:11.3f}{np.median(sub):9.3f}"
                  f"{np.percentile(sub, 90):9.3f}{brs[v] / best:10.2f}{mark}")

    # ---- the LEVEL anomaly ------------------------------------------------------------------
    # ⛔ CORRECTED SESSION 108: the premise below ("at blend = 1.0 the clean tap is fully out of
    # circuit, so LEVEL is a plain attenuator") is GATE K2's refuted one -- see the J8 note above.
    # LEVEL and bleed exposure are collinear here (r = -0.961), so the dependence this block
    # reports is LEVEL *and* dilution together, and the "structurally impossible" reading it was
    # written to support does not hold.  Kept because the MEASUREMENT stands; only the inference
    # from it was wrong.  GATE K3's matched-pair ladder is the instrument for the LEVEL law.
    # gain is therefore INVISIBLE to this statistic by construction, and band-RMS must not depend
    # on LEVEL at all.  It does (2.343 at 0.5 -> 4.873 at 1.0), so something is wrong, and the
    # cross-tab below says which KIND:
    #     penalty grows with stimulus level  => a NONLINEARITY downstream of LEVEL is engaging
    #                                           (the EQ mids boost up to +28 dB into TL07x rails)
    #     penalty flat across stimulus level => a LINEAR error (the LEVEL taper, or the
    #                                           LEVEL->BLEND pot loading circuit.md flags)
    print("\n-- J10: the LEVEL anomaly -- band-RMS must NOT depend on a post-OD attenuator --")
    print("    bleed-free rows only (blend = 1.0), ex HF.  Cells are band-RMS, (n) beneath.")
    sweeps = sorted({keys[r][1] for r in free})
    lv_hi = [r for r in free if caps[keys[r][0]]["settings"]["level"] == 1.0]
    lv_mid = [r for r in free if caps[keys[r][0]]["settings"]["level"] == 0.5]
    print(f"{'sweep':<16}{'LEVEL 0.5':>12}{'LEVEL 1.0':>12}{'ratio':>9}")
    lvl_out = {}
    for sw in sweeps:
        a = [r for r in lv_mid if keys[r][1] == sw]
        b = [r for r in lv_hi if keys[r][1] == sw]
        if not a or not b:
            print(f"{sw:<16}{'—':>12}{'—':>12}{'—':>9}   (one side empty)")
            continue
        ra, rb = band_rms_headline(dn[a]), band_rms_headline(dn[b])
        lvl_out[sw] = {"level_0.5": ra, "level_1.0": rb, "ratio": rb / ra,
                       "n_a": len(a), "n_b": len(b)}
        print(f"{sw:<16}{ra:12.3f}{rb:12.3f}{rb / ra:9.2f}")
        print(f"{'':16}{'(' + str(len(a)) + ')':>12}{'(' + str(len(b)) + ')':>12}")
    if not lvl_out:
        sys.exit("GATE J10 FAIL: no sweep has both LEVEL values -- the axes are confounded, "
                 "and the J9 level row must not be read as a level effect")

    # ---- J11: is LEVEL confounded with GRUNT, and is the penalty LEVEL or SHAPE? -------------
    # J9's two surviving effects are LEVEL and GRUNT.  They must be cross-tabbed before either is
    # believed: the level-varying captures include grunt variants, so an enriched grunt mix inside
    # the LEVEL-max bucket would manufacture the whole level effect (`defective-rows-must-not-vote`
    # in its confounding form).
    #
    # And each cell is split into a LEVEL term and a SHAPE term.  band-RMS pools both; re-anchoring
    # each row on its own non-HF mean removes the absolute offset and leaves the shape, so the two
    # can be read apart.
    # ⚠ The offset is measured against `gain_db_applied`, which comprehensive_report fits as a
    # broadband TIME-DOMAIN null gain over the whole sweep -- so it is pulled by the HF artefact
    # region GATE I identified (the model reads -10.1 dB there at LEVEL max).  Part of the "level
    # term" below is therefore that drag, NOT an OD-path level error.  It is an upper bound.
    print("\n-- J11: LEVEL x GRUNT, split into a LEVEL term and a SHAPE term (bleed-free, ex HF) --")
    sgn = signed_deltas(args.report, idx, args.method)
    bad = [k for k in list(od)[:200] if not np.allclose(np.abs(sgn[k]), od[k][0], atol=1e-12)]
    if bad:
        sys.exit(f"GATE J12 FAIL: signed loader disagrees with release_gate at {bad[:3]}")
    print(f"  J12 OK  signed loader reproduces |release_gate delta| on "
          f"{min(200, len(od))} rows")
    sn = np.vstack([sgn[k][non_hf] for k in keys])
    print(f"{'cell':<30}{'rows':>6}{'band-RMS':>10}{'shape':>9}{'level':>9}")
    x_out = {}
    for lv in sorted({caps[keys[r][0]]["settings"]["level"] for r in free}):
        for g in (0, 1, 2):
            rr = [r for r in free if caps[keys[r][0]]["settings"]["level"] == lv
                  and caps[keys[r][0]]["settings"]["gruntIdx"] == g]
            if len(rr) < 10:
                continue
            M = sn[rr]
            off = M.mean(axis=1, keepdims=True)
            cell = f"LEVEL {lv}  grunt {g}"
            x_out[cell] = {"rows": len(rr), "band_rms": band_rms_headline(M),
                           "shape": band_rms_headline(M - off),
                           "level": float(np.mean(np.abs(off)))}
            print(f"{cell:<30}{len(rr):6d}{x_out[cell]['band_rms']:10.3f}"
                  f"{x_out[cell]['shape']:9.3f}{x_out[cell]['level']:9.3f}")
    if len(x_out) < 4:
        sys.exit("GATE J11 FAIL: fewer than 4 well-supported cells -- the cross-tab cannot "
                 "separate LEVEL from GRUNT, so neither J9 row may be read as a main effect")
    print("\n  Both effects must hold WITHIN the other's cells to be real main effects.")

    if args.json:
        json.dump({"report": args.report, "method": used, "od_rows": len(od),
                   "headline_band_rms": headline, "pooled_rms": float(np.sqrt(pooled_ms)),
                   "per_band": per_band, "ex_hf": ex, "full": full,
                   "band_rms_ex_hf": h_ex, "mid_subs": mid_out, "axes": axis_out,
                   "a3": a3_out, "n_free": len(free), "n_bled": len(bled)},
                  open(args.json, "w"), indent=1)
        print(f"\n  wrote {args.json}")


if __name__ == "__main__":
    main()
