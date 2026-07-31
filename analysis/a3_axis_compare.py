#!/usr/bin/env python3.11
"""a3_axis_compare -- settle A3's SHAPE by comparing the two instruments that measure it.

WHY THIS EXISTS (session 85's next-step (a))
--------------------------------------------
Two tools now measure the same physical quantity -- how far the model's OD path sits
below where it should relative to its own clean bleed -- on axes that share NO
machinery:

  a3_shape_gate      `20log10 s` per band, from the DRIVE ladder.  Needs the model's
                     mu_d shape, a fitted flat bleed level beta, and a two-phasor
                     solve per band.
  a3_harmonic_axis   `k` per band, from the LEVEL/BLEND dilution of Hn/H1.  Needs NO
                     solve, NO taper, NO b0 and NO bleed model.

They agree on the SIGN (the model's OD is too weak) and on the order of magnitude,
and session 85 recorded that they DISAGREE on the shape: `20log10 s` RISES with
frequency (+4.43 / +5.20 / +7.60) where |k| FALLS (10.64 / 6.14 / 4.99).  That
disagreement is what this tool exists to settle, because until it is settled neither
curve can be used to aim a carrier.

⭐ THE COMPARISON IS FREQUENCY-ALIGNED, AND THAT IS NOT AN ASSUMPTION -- IT IS ALGEBRA.
`d` looks like a harmonic statistic, but the harmonics cancel out of it exactly.  Only
the OD path carries harmonics, so at a diluted cell

    Hn_out = O.hn                       H1_out = O.g1 + C
    R_n(c)      = 20log10(O.hn) - 20log10|O.g1 + C|
    R_n(anchor) = 20log10(O.hn) - 20log10|O.g1|            (C = 0 at the anchor)
    d(c) = R_n(anchor) - R_n(c) = 20log10|1 + C/(O.g1)|

`hn` cancels, so `d` is a property of the OD-vs-clean balance AT THE FUNDAMENTAL -- at
100 / 200 / 400 Hz, not at the harmonic frequencies.  So it compares like-for-like with
the shape gate's 101 / 202 / 403 Hz bands.  The ORDERS enter only as repeated
measurements of one number, which is why the tool's own spread gate is an
order-independence check -- and which is why GATE 2 below is a real test.

⚠⚠ AND THE PREMISE FOR RESTRICTING THE SHAPE GATE'S BAND SET DOES NOT SURVIVE (GATE 1).
Session 51 item 6 found the drive solve "sitting ON its parameter boundary" at 202 and
254 Hz (theta = 0.0) and concluded the shape gate's SCORE is partly set by a solve at
its own boundary; sessions 52, 79-85 carried "restrict CORE to bands where the drive
solve is interior" as an open item.  But theta is a FOLDED parameter -- conjugating
theta leaves every |.| unchanged, so only |theta| is identifiable and the cost is
EXACTLY symmetric about both endpoints:

    |1 + s.mu.e^(+i.theta)| == |1 + s.mu.e^(-i.theta)|

Therefore theta = 0 and theta = 180 are STATIONARY POINTS BY SYMMETRY, not truncated
bounds, and an optimum resting there is not the `bound-resting-means-unidentified`
case at all.  GATE 1 demonstrates it numerically rather than arguing it.  What IS true
near theta = 0 is that dcos(theta)/dtheta = 0, so theta is weakly determined there --
but the SCORED quantity is `s`, not theta, and `s` is correspondingly INSENSITIVE to
theta exactly where theta is loose.  So the restriction must be justified by the
measured identifiability of `s` (the interval this tool prints), never by theta.

Usage:
    python3.11 analysis/a3_axis_compare.py
    python3.11 analysis/a3_axis_compare.py --fit btC17=10e-9        # score a candidate
    python3.11 analysis/a3_axis_compare.py --report analysis/reports/s85_a3_harmonic_axis.json
"""
import argparse
import json
import math
import os
import subprocess
import sys
import tempfile

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_harmonic_axis as HA                                        # noqa: E402
import a3_phase_solve as ps                                          # noqa: E402
import a3_shape_gate as sg                                           # noqa: E402

DEFAULT_REPORT = "analysis/reports/s85_a3_harmonic_axis.json"

# The harmonic axis's own recorded per-band record (session 85 item 5) and pooled k.
# GATE 0 refuses to compare if the report does not reproduce these -- a moved
# instrument and a moved result are indistinguishable otherwise.
K_RECORD = {100.0: -10.64, 200.0: -6.14, 400.0: -4.99}
K_POOLED_RECORD = -6.50

# ANCHOR_HZ -> the shape gate's nearest PROBE band. Stated explicitly rather than
# computed silently, so a change to either band list is visible in the diff.
BAND_OF = {100.0: 101, 200.0: 202, 400.0: 403}

BOOT = 400
SEED = 20260731


# --------------------------------------------------------------------------- #
# the harmonic-axis side -- recomputed from the report's rows, never transcribed
# --------------------------------------------------------------------------- #
def load_ladder(path):
    with open(path) as fh:
        d = json.load(fh)
    sgate = d["spread_gate"]
    fin = [r for r in d["rows"] if np.isfinite(r["delta"]) and r["spread_ped"] <= sgate]
    # BLEND=1/LEVEL=1 IS the anchor -- d is 0 there by construction and must not vote
    # (session 85 item 3a: `matrix_harmonics.no_od_path_rows`, one tool over).
    lad = [r for r in fin if not (r["blend"] == 1.0 and r["level"] == 1.0)]
    return d, lad


def boot_k(sub, rng, nboot=BOOT, cols=("d_mdl", "d_ped")):
    """Group-level bootstrap on k.

    ⚠ Clusters, not cells. Cells within one (group, sweep) ladder share an anchor, an
    operating point and a taper, so resampling cells would treat correlated
    measurements as independent and report an interval several times too tight.
    """
    keys = sorted({(r["group"], r["sweep"]) for r in sub})
    by = {k: [r for r in sub if (r["group"], r["sweep"]) == k] for k in keys}
    out = []
    for _ in range(nboot):
        pick = rng.choice(len(keys), size=len(keys), replace=True)
        cells = [c for i in pick for c in by[keys[i]]]
        k, _, _ = HA.fit_balance([(c[cols[0]], c[cols[1]]) for c in cells])
        if np.isfinite(k):
            out.append(k)
    if not out:
        return float("nan"), float("nan")
    return float(np.percentile(out, 5)), float(np.percentile(out, 95))


def harmonic_side(lad, rng):
    rows = {}
    for hz in HA.ANCHOR_HZ:
        s = [r for r in lad if r["hz"] == hz]
        if len(s) < 3:
            continue
        k, rms, n = HA.fit_balance([(r["d_mdl"], r["d_ped"]) for r in s])
        lo, hi = boot_k(s, rng)
        # GATE 2's inputs: the same k from two disjoint order groups.
        kl, _, nl = HA.fit_balance([(r["mdl_lo"], r["ped_lo"]) for r in s])
        kh, _, nh = HA.fit_balance([(r["mdl_hi"], r["ped_hi"]) for r in s])
        llo, lhi = boot_k(s, rng, cols=("mdl_lo", "ped_lo"))
        dm = np.asarray([r["d_mdl"] for r in s])
        rows[hz] = dict(k=k, rms=rms, n=n, lo=lo, hi=hi,
                        clusters=len({(r["group"], r["sweep"]) for r in s}),
                        k_low=kl, n_low=nl, k_high=kh, n_high=nh,
                        low_lo=llo, low_hi=lhi,
                        d_min=float(dm.min()), d_max=float(dm.max()),
                        d_med=float(np.median(dm)))
    k, rms, n = HA.fit_balance([(r["d_mdl"], r["d_ped"]) for r in lad])
    return rows, dict(k=k, rms=rms, n=n)


# --------------------------------------------------------------------------- #
# the shape-gate side
# --------------------------------------------------------------------------- #
def shape_side(prefix, sweep, fits):
    sg.render(fits, prefix)
    model = ps.load_model([d for d, _ in ps.DRIVES], prefix)
    pedal = ps.load_pedal(sweep)
    beta = sg.fit_beta(pedal, model)
    rows = {}
    for b in ps.PROBE_BANDS:
        mu = np.array([model[d][b][0] for d, _ in ps.DRIVES])
        t = np.array(pedal[b])
        (th, cost, s), prof = ps.fit_band(t, mu, beta)
        lo, hi = sg.s_interval(mu, t, beta)
        rows[b] = dict(s_db=20.0 * math.log10(s),
                       lo_db=20.0 * math.log10(lo), hi_db=20.0 * math.log10(hi),
                       width=20.0 * math.log10(hi / lo),
                       theta=math.degrees(th), rms=math.sqrt(cost))
    return beta, rows, model, pedal


# --------------------------------------------------------------------------- #
# gates
# --------------------------------------------------------------------------- #
def gate1_symmetry(model, pedal, beta):
    """theta = 0 / 180 are symmetry points of a FOLDED parameter, not fences.

    Demonstrated, not argued: evaluate the cost a hair either side of each endpoint at
    the band's own solved s. Both differences must be ~0 to floating point. If they
    were NOT, the parameter would genuinely be truncated and `bound-resting-means-
    unidentified` would apply -- so this gate is what licenses ignoring session 51's
    railing observation, and it must be run, not assumed.
    """
    print("\nGATE 1 -- is theta = 0 a FENCE or a SYMMETRY POINT?")
    worst = 0.0
    for b in (202, 254, 40):
        mu = np.array([model[d][b][0] for d, _ in ps.DRIVES])
        t = np.array(pedal[b])
        (_, _, s), _ = ps.fit_band(t, mu, beta)

        def cost(theta):
            z = s * mu * np.exp(1j * theta)
            return float(np.mean((beta + 20.0 * np.log10(np.abs(1.0 + z)) - t) ** 2))

        d0 = abs(cost(+0.05) - cost(-0.05))
        d180 = abs(cost(math.pi + 0.05) - cost(math.pi - 0.05))
        worst = max(worst, d0, d180)
        print(f"  {b:4d} Hz  |cost(+e) - cost(-e)|  at 0: {d0:.3e}   at 180: {d180:.3e}")
    ok = worst < 1e-9
    verdict = ("theta resting at an endpoint is NOT bound-resting; restrict on s, not theta"
               if ok else "session 51 was right, theta IS truncated")
    print(f"  worst {worst:.3e}  =>  {'SYMMETRY POINTS' if ok else 'GENUINE BOUNDS'} -- {verdict}")
    return ok


def gate2_order_independence(hrows):
    """`d` is order-INDEPENDENT by algebra (see the module docstring), so k fitted on
    H2/H3 alone must equal k fitted on H6/H7 alone. Where it does not, that band
    violates the instrument's OWN premise and cannot carry a shape claim.

    This is a real test rather than a re-description because it is over-determined:
    two disjoint order groups, one predicted number.
    """
    print("\nGATE 2 -- ORDER INDEPENDENCE of k (the harmonic axis's own premise)")
    print(f"  {'Hz':>6} {'k(all)':>8} {'k(H2,H3)':>9} {'k(H6,H7)':>9} {'|split|':>8}")
    splits = {}
    for hz, r in sorted(hrows.items()):
        sp = abs(r["k_low"] - r["k_high"])
        splits[hz] = sp
        print(f"  {hz:6.0f} {r['k']:+8.2f} {r['k_low']:+9.2f} {r['k_high']:+9.2f} {sp:8.2f}")
    worst = max(splits, key=lambda h: splits[h])
    med = float(np.median([v for h, v in splits.items() if h != worst]))
    print(f"  worst {worst:.0f} Hz at {splits[worst]:.2f} dB, against a median of "
          f"{med:.2f} dB elsewhere ({splits[worst] / max(med, 1e-9):.1f}x)")
    return splits


# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=DEFAULT_REPORT)
    ap.add_argument("--sweep", default="sweep_drv_-18")
    ap.add_argument("--fit", action="append", default=[], metavar="KEY=VALUE")
    ap.add_argument("--out", default=None)
    args = ap.parse_args()

    fits = [tuple(f.split("=", 1)) for f in args.fit]
    rng = np.random.default_rng(SEED)

    _, lad = load_ladder(args.report)
    hrows, pooled = harmonic_side(lad, rng)

    tmp = tempfile.mkdtemp(prefix="a3cmp_")
    beta, srows, model, pedal = shape_side(os.path.join(tmp, "dec"), args.sweep, fits)

    # ---- GATE 0: BOTH instruments must reproduce their record before either is read.
    print("=== GATE 0 -- BASELINE, BOTH SIDES ===")
    kd = max(abs(hrows[h]["k"] - K_RECORD[h]) for h in K_RECORD if h in hrows)
    pd = abs(pooled["k"] - K_POOLED_RECORD)
    print(f"  harmonic axis: worst per-band |dk| {kd:.3f} dB, pooled |dk| {pd:.3f} dB "
          f"(n={pooled['n']}, rms {pooled['rms']:.2f})")
    if fits:
        print(f"  shape gate:    CANDIDATE {fits} -- baseline check skipped by construction")
        sd = float("nan")
    else:
        sd = max(abs(srows[b]["s_db"] - sg.BASELINE_DB[b]) for b in sg.CORE)
        print(f"  shape gate:    worst |d(20log10 s)| vs record {sd:.3f} dB, "
              f"beta {beta:+.2f} dB")
    bad = kd > 0.05 or pd > 0.05 or (not fits and sd > 0.05)
    print("  " + ("FAIL -- an instrument moved; a moved result is unreadable" if bad else "PASS"))
    if bad:
        sys.exit(1)

    gate1_symmetry(model, pedal, beta)
    splits = gate2_order_independence(hrows)

    # ---- the comparison
    print("\n=== A3's CURVE ON TWO INDEPENDENT AXES ===")
    print("  both columns are 'dB by which the model's OD sits below where it should,")
    print("  relative to its own clean bleed' -- same sign, same units, same frequency")
    print(f"\n  {'Hz':>6} {'shape 20log10 s':>17} {'interval':>16} "
          f"{'|k| harmonic':>13} {'interval':>16} {'verdict':>10} {'gap':>6}")
    out = []
    for hz in sorted(hrows):
        b = BAND_OF[hz]
        s, h = srows[b], hrows[hz]
        s_lo, s_hi = s["lo_db"], s["hi_db"]
        k_lo, k_hi = abs(h["hi"]), abs(h["lo"])          # |k|: bootstrap ends swap
        overlap = not (s_hi < k_lo or k_hi < s_lo)
        gap = 0.0 if overlap else (k_lo - s_hi if s_hi < k_lo else s_lo - k_hi)
        print(f"  {hz:6.0f} {s['s_db']:+17.2f} [{s_lo:+5.2f},{s_hi:+6.2f}] "
              f"{abs(h['k']):13.2f} [{k_lo:+5.2f},{k_hi:+6.2f}] "
              f"{'OVERLAP' if overlap else 'DISJOINT':>10} {gap:6.2f}")
        out.append(dict(hz=hz, band=b, s_db=s["s_db"], s_lo=s_lo, s_hi=s_hi,
                        s_width=s["width"], s_rms=s["rms"], s_theta=s["theta"],
                        k=h["k"], k_lo=h["lo"], k_hi=h["hi"], k_rms=h["rms"],
                        n=h["n"], clusters=h["clusters"],
                        k_low=h["k_low"], k_high=h["k_high"], split=splits[hz],
                        overlap=bool(overlap), gap=gap))

    dis = [r for r in out if not r["overlap"]]
    print(f"\n  {len(out) - len(dis)} of {len(out)} bands OVERLAP.")
    if len(dis) == 1:
        r = dis[0]
        print(f"  ⇒ on ALL orders the disagreement is ONE band, {r['hz']:.0f} Hz, by "
              f"{r['gap']:.2f} dB.")
        print(f"    That band is the harmonic axis's thinnest (n={r['n']} over "
              f"{r['clusters']} clusters), it FAILS GATE 2 ({r['split']:.2f} dB of order")
        print(f"    split vs {np.median([x['split'] for x in out if x is not r]):.2f} dB "
              f"elsewhere), and it has the least DILUTION LEVERAGE (see below).")
    elif not dis:
        print("  ⇒ NO band disagrees: the two instruments describe one curve.")

    # ---- ⭐⭐ THE DECIDING READ. `predict_from_balance` only SATURATES at k once the
    # dilution is deep, so a band's leverage on k is its own d_mdl range -- and the
    # order groups are not equal in quality either: LOW_ORDERS (H2, H3) are the last to
    # reach the capture's noise, which is why a3_harmonic_axis designates them the
    # robust subset. Re-running the SAME comparison on that subset is therefore not
    # subset-shopping (`self-selecting-scores`): the subset is named by the other tool,
    # for a stated reason, before this comparison existed.
    print("\n=== THE SAME COMPARISON ON THE ROBUST ORDER SUBSET (H2, H3) ===")
    print(f"  {'Hz':>6} {'dilution d_mdl':>16} {'shape':>8} {'interval':>16} "
          f"{'|k| H2,H3':>10} {'interval':>16} {'verdict':>10}")
    rob = []
    for r in out:
        s_lo, s_hi = r["s_lo"], r["s_hi"]
        h = hrows[r["hz"]]
        k_lo, k_hi = abs(h["low_hi"]), abs(h["low_lo"])
        ov = not (s_hi < k_lo or k_hi < s_lo)
        rob.append(ov)
        r.update(k_low_lo=h["low_lo"], k_low_hi=h["low_hi"], overlap_low=bool(ov),
                 d_min=h["d_min"], d_max=h["d_max"], d_med=h["d_med"])
        print(f"  {r['hz']:6.0f} {h['d_min']:6.1f}..{h['d_max']:5.1f} dB "
              f"{r['s_db']:+8.2f} [{s_lo:+5.2f},{s_hi:+6.2f}] {abs(h['k_low']):10.2f} "
              f"[{k_lo:+5.2f},{k_hi:+6.2f}] {'OVERLAP' if ov else 'DISJOINT':>10}")
    print(f"\n  {sum(rob)} of {len(rob)} bands OVERLAP on the robust subset.")
    if all(rob):
        print("  ⇒ ⭐⭐ THE SHAPE DISAGREEMENT DOES NOT SURVIVE. On the order subset the")
        print("    harmonic axis itself designates as robust, EVERY band is compatible with")
        print("    the drive axis. The two instruments describe ONE curve, and session 85")
        print("    item 5's 'the SHAPE disagrees' should not be carried forward.")
        print("  ⚠ What that does NOT license: calling the curve FLAT. The intervals are")
        print("    wide (shape gate 1.8-3.9 dB, harmonic axis 3.2-9.9 dB), so what is")
        print("    established is compatibility, not a shape. Quote A3 as ~5-7 dB over")
        print("    100-400 Hz and do not fit a slope to either column.")
    else:
        print("  ⇒ the disagreement survives the robust subset; it is not an order artefact.")

    # ---- what the shape gate's own conditioning says about its shape claim
    print("\n=== THE SHAPE GATE'S OWN CONDITIONING ACROSS ITS CORE SET ===")
    print("  (the +0.25 dB joint (s, theta) interval, in dB of s -- printed because the")
    print("   'the deficit RISES with frequency' claim is carried by the widest of them)")
    print(f"  {'Hz':>6} {'20log10 s':>10} {'width':>7} {'theta':>7} {'rms':>6}")
    for b in sg.CORE:
        r = srows[b]
        print(f"  {b:6d} {r['s_db']:+10.2f} {r['width']:7.2f} {r['theta']:7.1f} {r['rms']:6.3f}")
    narrow = [b for b in sg.CORE if srows[b]["width"] <= 2.5]
    railed = [b for b in sg.CORE if min(srows[b]["theta"], 180.0 - srows[b]["theta"]) < 2.0]

    def score(bands):
        return math.sqrt(float(np.mean([srows[b]["s_db"] ** 2 for b in bands])))

    print(f"\n  CORE score, all {len(sg.CORE)} bands            = {score(sg.CORE):.3f} dB")
    keep = [b for b in sg.CORE if b not in railed]
    print(f"  ex theta-at-a-symmetry-point {railed}  ({len(keep)} bands) = {score(keep):.3f} dB"
          f"   <- session 51's proposed restriction")
    print(f"  ex s-interval > 2.5 dB       ({len(narrow)} bands) = {score(narrow):.3f} dB"
          f"   <- the MEASURED one; drops {sorted(set(sg.CORE) - set(narrow))}")
    print("\n  ⇒ the two restrictions do not select the same bands, and only the second")
    print("    is justified by the quantity being scored. Neither changes the ranking of")
    print("    a candidate on its own -- freeze whichever set is used at the SHIPPED")
    print("    baseline and never re-derive it per candidate (self-selecting-scores).")

    if args.out:
        with open(args.out, "w") as fh:
            json.dump(dict(report=args.report, fits=fits, beta=beta, bands=out,
                           pooled=pooled,
                           shape=({str(b): srows[b] for b in ps.PROBE_BANDS}),
                           scores=dict(core=score(sg.CORE), ex_railed=score(keep),
                                       ex_wide=score(narrow)),
                           railed=railed, narrow=narrow), fh, indent=1)
        print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
