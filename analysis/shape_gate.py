#!/usr/bin/env python3.11
"""FR and THD as CURVES: decompose every residual into LEVEL + TILT + CURVATURE + LOCAL.
Session 63, Phase 9. A shape layer over the existing reports -- it changes no oracle and no record.

WHY THIS EXISTS
---------------
`matrix_grade.py` reports a band-RMS and a two-region tilt per row. Both are real, and both are
AGGREGATES -- and this project's most expensive misses were all things an aggregate cannot express:

  * The ~320 Hz cancellation notch survived FORTY-SIX sessions. Session 19 fitted
    `trebleLadderDampR` against "-3.4 dB in the capture", which was a 1/3-octave POINT SAMPLE of a
    notch centred 316-334 Hz -- understating it by up to 20 dB (session 46). Every gate in between
    read one number, and a notch contributes almost nothing to a 26-band RMS.
  * "A3 is below ~200 Hz" survived to session 46 for the same reason, and needed a whole new
    instrument (session 47's a3_shape_gate.py) to be seen as the broadband bathtub it is.
  * Session 60 item 8b -- ATTACK moving the null, the finding this entire A3 branch now rests on --
    was found BY THE USER READING AN FR CHART, not by any gate in the tree.

The common failure is not resolution and not accuracy. It is that a single scalar cannot distinguish
"the whole curve is 1 dB high" from "the curve tilts 2 dB across the band" from "there is a 20 dB
notch at 320 Hz" -- and those three have completely different causes and completely different fixes.
So decompose the residual instead of summarising it.

THE DECOMPOSITION
-----------------
For each row, residual d(f) = plugin_dB - pedal_dB over the graded bands. Fit an ORTHONORMAL basis
in u = normalised log f:

    LEVEL      constant        -> a gain-match / makeup offset, or a real broadband level error
    TILT       linear in u     -> one wrong corner, a taper, a bass/treble balance
    CURVATURE  quadratic in u  -> a bump or a scoop (a bridged-T, a mid peak)
    LOCAL      what is LEFT    -> narrow features: notches, peaks, resonances

Because the basis is orthonormal, the four terms partition the mean square EXACTLY:

    rms(d)^2  =  level^2 + tilt^2 + curvature^2 + local^2

and the LOCAL row is the one no previous gate had. It is where a notch lives: the tool also reports
the worst single LOCAL band and its frequency, which is a notch DETECTOR rather than a measurement.

⚠ THE GROUP TOTAL HERE IS **NOT** `matrix_grade`'s NUMBER, AND A FIRST DRAFT OF THIS DOCSTRING
CLAIMED IT WAS. `matrix_grade` aggregates rows by ARITHMETIC mean of their per-row band-RMS; this
tool must use the QUADRATIC mean (rms of rms), because only that makes the four terms partition the
group total as well as each row. The two differ systematically -- quadratic >= arithmetic, and on the
frozen baseline it is 2.611 vs 1.903 for OD ex gain-n12 -- so reading this tool's total as a
regression against matrix_grade's would be pure arithmetic. Both are printed side by side below;
neither replaces the other, and `matrix_grade` remains the headline grade.

⚠ LOCAL IS NOT A SUBSTITUTE FOR RESOLUTION. On the 1/3-octave grid a local excursion is a lower
bound on a narrow feature's depth -- session 46 measured the same notch as -3.4 dB banded and up to
-24 dB at full resolution. LOCAL tells you WHERE to go and look at 5.86 Hz bins (that is what
attack_notch_probe.py / attack_render_gate.py are for); it does not tell you how deep the thing is.

THD IS TREATED AS A CURVE TOO, AND IN dB
----------------------------------------
THD is a RATIO, so it is decomposed in dB (20log10 of the percentage), not in percent -- otherwise a
multiplicative error at high THD swamps the same error at low THD and the "shape" is just wherever
the pedal happens to distort most. Two curves are reported:

  * THD vs FREQUENCY, decomposed exactly as FR is.
  * THD vs STIMULUS LEVEL -- the COMPRESSION curve, per band. This is the axis that has decided
    several arguments in this project (session 57's reading (i) vs (ii) turned entirely on whether an
    effect faded toward the linear regime; session 59 showed the drive axis trades compression
    against sensitivity in BOTH directions), and no per-row aggregate contains it at all.

GATES
-----
  1 EXACTNESS   the four terms must partition the mean square to ~1e-12 (it is an orthonormal
                projection, so anything else is a bug in the basis).
  2 ATTRIBUTION synthetic residuals of KNOWN shape -- pure offset, pure tilt, pure scoop, and a
                single-band notch -- must land in the right term and (for the notch) at the right
                frequency. A decomposition that cannot attribute a shape it was handed is not
                evidence about a shape it was not.
  3 MEMBERSHIP  every aggregate is over ONE fixed band set and ONE row set, printed. An rms over
                differently-populated rows is not a ranking (the session-49 item-7 trap, hit four
                separate times in this project).

Usage:
  python3.11 analysis/shape_gate.py REPORT.json [--vs OTHER.json] [--selftest]
                                    [--only SUBSTR] [--png OUT] [--json OUT] [--top N]
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import matrix_grade as MG                              # noqa: E402

GRADE_LO, GRADE_HI = MG.GRADE_LO, MG.GRADE_HI
SILENT_DB = MG.SILENT_DB
TERMS = ["level", "tilt", "curv", "local"]


# =============================================================================================
# the decomposition
# =============================================================================================
def basis(freqs):
    """Orthonormal {1, u, u^2} on u = normalised log10(f). Orthonormal so the terms partition the
    mean square exactly rather than approximately -- which is what makes the sum a CHECK."""
    lg = np.log10(np.asarray(freqs, dtype=float))
    u = 2.0 * (lg - lg.min()) / (lg.max() - lg.min()) - 1.0
    V = np.stack([np.ones_like(u), u, u * u], axis=1)
    Q, _ = np.linalg.qr(V)                             # columns orthonormal
    return Q


def decompose(d, Q):
    """-> dict of per-term rms (dB) + the LOCAL curve. rms(d)^2 == sum(term^2) exactly."""
    d = np.asarray(d, dtype=float)
    n = len(d)
    c = Q.T @ d                                        # projection coefficients
    loc = d - Q @ c
    out = {"level": abs(float(c[0])) / np.sqrt(n),
           "tilt": abs(float(c[1])) / np.sqrt(n),
           "curv": abs(float(c[2])) / np.sqrt(n),
           "local": float(np.sqrt(np.mean(loc ** 2))),
           "rms": float(np.sqrt(np.mean(d ** 2))),
           # signed versions, because the DIRECTION of a tilt is the diagnostic half
           "level_signed": float(c[0]) / np.sqrt(n),
           "tilt_signed": float(c[1]) / np.sqrt(n),
           "curv_signed": float(c[2]) / np.sqrt(n)}
    out["local_curve"] = loc
    return out


def local_interior(loc, freqs, drop=2):
    """LOCAL rms with the outermost `drop` bands each side removed.

    ⚠ THIS IS A CONTROL, NOT A REFINEMENT. A least-squares polynomial has its worst leverage at the
    ENDS of the fit range, so a smooth-but-unmodelled roll-off at 25 Hz or 12.9 kHz lands in LOCAL
    and can masquerade as narrow structure. The first run of this tool put every one of its worst
    LOCAL bands at 25-32 Hz or 4-13 kHz, which is exactly what that artefact looks like -- so the
    interior-only number is printed beside the full one, and any claim that LOCAL dominates has to
    survive it.
    """
    if len(loc) <= 2 * drop + 3:
        return float(np.sqrt(np.mean(loc ** 2)))
    return float(np.sqrt(np.mean(loc[drop:-drop] ** 2)))


def worst_local(loc, freqs):
    i = int(np.argmax(np.abs(loc)))
    return float(loc[i]), float(freqs[i])


# =============================================================================================
# gates
# =============================================================================================
def selftest():
    print("=" * 104)
    print("GATES")
    print("=" * 104)
    ok = True
    freqs = [20.0 * 2 ** (k / 3.0) for k in range(30)]
    fa = np.array(freqs)
    Q = basis(freqs)

    print("  1 EXACTNESS -- the four terms must partition the mean square")
    rng = np.random.default_rng(7)
    worst = 0.0
    for _ in range(200):
        d = rng.normal(0.0, 3.0, len(freqs))
        r = decompose(d, Q)
        lhs = r["rms"] ** 2
        rhs = sum(r[t] ** 2 for t in TERMS)
        worst = max(worst, abs(lhs - rhs))
    print("      worst |rms^2 - sum(term^2)| over 200 random residuals: %.3e   %s"
          % (worst, "OK" if worst < 1e-9 else "FAIL"))
    ok &= worst < 1e-9

    print("\n  2 ATTRIBUTION -- synthetic residuals of KNOWN shape must land in the right term")
    lg = np.log10(fa)
    u = 2.0 * (lg - lg.min()) / (lg.max() - lg.min()) - 1.0
    cases = [
        ("pure offset  +2.0 dB", np.full(len(fa), 2.0), "level"),
        ("pure tilt    +-3 dB", 3.0 * u, "tilt"),
        ("pure scoop         ", 4.0 * (u * u - np.mean(u * u)), "curv"),
        ("one-band notch -12 ", np.where(np.abs(fa - 320.0) < 12.0, -12.0, 0.0), "local"),
    ]
    print("      %-22s %8s %8s %8s %8s   %-9s %s"
          % ("case", "level", "tilt", "curv", "local", "expected", "verdict"))
    for name, d, want in cases:
        r = decompose(d, Q)
        got = max(TERMS, key=lambda t: r[t])
        good = got == want
        ok &= good
        print("      %-22s %8.2f %8.2f %8.2f %8.2f   %-9s %s"
              % (name, r["level"], r["tilt"], r["curv"], r["local"], want,
                 "OK" if good else "FAIL (got %s)" % got))
        if want == "local":
            v, fw = worst_local(r["local_curve"], fa)
            near = abs(fw - 320.0) < 40.0
            ok &= near
            print("      %-22s worst LOCAL %+.2f dB at %.1f Hz (injected at 320)   %s"
                  % ("", v, fw, "OK" if near else "FAIL -- wrong frequency"))
    # ⚠ A notch confined to ONE band is only partly local: a quadratic can chase it a little, so
    # the local term is a LOWER bound on the feature. Show that rather than implying it is exact.
    d = np.where(np.abs(fa - 320.0) < 12.0, -12.0, 0.0)
    r = decompose(d, Q)
    cap = r["local"] / r["rms"]
    print("      ⚠ a 1-band -12 dB notch lands %.0f%% in LOCAL, not 100%% -- the smooth terms chase"
          % (100.0 * cap))
    print("        it slightly, so LOCAL is a LOWER BOUND on a narrow feature (and the 1/3-oct grid")
    print("        is a second, larger lower bound -- session 46 measured -3.4 banded vs -24 at")
    print("        full resolution). LOCAL says WHERE to look, not how deep.")
    print("\n  %s" % ("GATES PASS" if ok else "GATES FAIL"))
    return ok


# =============================================================================================
# rows
# =============================================================================================
def fr_rows(path, only=None):
    bands, caps = MG.load(path)
    idx = MG.band_idx(bands, GRADE_LO, GRADE_HI)
    fs = [bands[i] for i in idx]
    Q = basis(fs)
    rows = {}
    for f, c in caps.items():
        if only and only not in f:
            continue
        for sw, fr in c["fr"].items():
            p, q = fr["plugin_db"], fr["pedal_db"]
            if max(p) < SILENT_DB or max(q) < SILENT_DB:
                continue
            d = np.array([p[i] - q[i] for i in idx])
            r = decompose(d, Q)
            r["worst_local"], r["worst_local_hz"] = worst_local(r["local_curve"], fs)
            r["local_int"] = local_interior(r["local_curve"], fs)
            r["is_od"] = MG.is_od(f)
            rows[(f, sw)] = r
    return fs, rows


def thd_rows(path, only=None):
    """THD residual in dB (a ratio -> log domain), decomposed exactly as FR is."""
    bands, caps = MG.load(path)
    idx = MG.band_idx(bands, GRADE_LO, GRADE_HI)
    fs = [bands[i] for i in idx]
    Q = basis(fs)
    FLOOR = 1e-3                                       # 0.001 % -- the measurement floor
    rows, level_curve = {}, {}
    for f, c in caps.items():
        if only and only not in f:
            continue
        for sw, th in c.get("thd", {}).items():
            pp, qq = th["plugin_pct"], th["pedal_pct"]
            # Only bands where BOTH sides are above the floor: a ratio against a floor value is
            # not a measurement, and including it manufactures huge dB errors out of noise.
            # ⚠ None appears above the THD Nyquist guard (analyze.thd_max_measurable_hz)
            # -- a missing measurement, not a zero. Drop those bands rather than
            # coercing them, or the ratio invents structure where there is no data.
            use = [i for i in idx
                   if pp[i] is not None and qq[i] is not None
                   and pp[i] > FLOOR and qq[i] > FLOOR]
            if len(use) < 8:
                continue
            d = np.array([20.0 * np.log10(pp[i] / qq[i]) for i in use])
            Qu = basis([bands[i] for i in use])
            r = decompose(d, Qu)
            r["worst_local"], r["worst_local_hz"] = worst_local(
                r["local_curve"], [bands[i] for i in use])
            r["local_int"] = local_interior(r["local_curve"], [bands[i] for i in use])
            r["n_bands"] = len(use)
            r["is_od"] = MG.is_od(f)
            rows[(f, sw)] = r
            level_curve.setdefault(f, {})[sw] = float(np.mean(d))
    return fs, rows, level_curve


def aggregate(rows, label, note=""):
    """⚠ One fixed row set per line, with its COUNT printed -- an rms over differently-populated
    groups is not a ranking (session 49 item 7; this project hit that trap four times)."""
    if not rows:
        return None
    out = {"n": len(rows), "label": label}
    for t in TERMS + ["rms", "local_int"]:
        out[t] = float(np.sqrt(np.mean([r[t] ** 2 for r in rows])))
    # signed means, so a systematic tilt does not cancel itself in an rms
    for t in ("level_signed", "tilt_signed", "curv_signed"):
        out[t] = float(np.mean([r[t] for r in rows]))
    # matrix_grade's own convention, printed beside the quadratic one so the two are comparable
    # rather than one silently standing in for the other.
    out["rms_arith"] = float(np.mean([r["rms"] for r in rows]))
    i = int(np.argmax([abs(r["worst_local"]) for r in rows]))
    out["worst_local"] = rows[i]["worst_local"]
    out["worst_local_hz"] = rows[i]["worst_local_hz"]
    print("  %-26s %4d %7.3f = %6.3f %6.3f %6.3f %6.3f | %6.3f %7.3f  %+7.2f @ %6.0f %s"
          % (label, out["n"], out["rms"], out["level"], out["tilt"], out["curv"], out["local"],
             out["local_int"], out["rms_arith"], out["worst_local"], out["worst_local_hz"], note))
    return out


def group(rows, pred):
    return [r for k, r in rows.items() if pred(k, r)]


def report(title, rows, top):
    print("\n" + "=" * 104)
    print(title)
    print("=" * 104)
    print("  %-26s %4s %7s   %-27s | %6s %7s  %s"
          % ("group", "rows", "rms(q)", "= level  tilt   curv  local", "int'r", "rms(a)",
             "worst LOCAL band"))
    print("      rms(q) = quadratic mean (partitions into the 4 terms) | int'r = LOCAL with the 2")
    print("      outermost bands each side dropped (EDGE CONTROL) | rms(a) = matrix_grade's mean")
    aggs = {}
    n12 = lambda k: "gain-n12" in k[0]                                             # noqa: E731
    aggs["OD ex gain-n12"] = aggregate(group(rows, lambda k, r: r["is_od"] and not n12(k)),
                                       "OD ex gain-n12")
    aggs["OD gain-n12"] = aggregate(group(rows, lambda k, r: r["is_od"] and n12(k)),
                                    "OD gain-n12 [bad]",
                                    "<- capture defect, session 48")
    aggs["CLEAN"] = aggregate(group(rows, lambda k, r: not r["is_od"]), "CLEAN")
    aggs["ALL"] = aggregate(list(rows.values()), "ALL")
    print("\n  ⭐ READ THE DECOMPOSITION, NOT THE TOTAL: the four columns partition the rms exactly,")
    print("     so a big `local` is a NARROW FEATURE (go and look at full resolution) while a big")
    print("     `tilt` is a corner/taper and a big `level` is gain-staging. They need different fixes.")

    print("\n  worst %d rows by LOCAL (the notch detector):" % top)
    print("  %-46s %-14s %7s %7s   %s" % ("row", "sweep", "rms", "local", "worst LOCAL band"))
    for (f, sw), r in sorted(rows.items(), key=lambda kv: -kv[1]["local"])[:top]:
        print("  %-46s %-14s %7.3f %7.3f   %+7.2f dB @ %6.0f Hz"
              % (f[:46], sw, r["rms"], r["local"], r["worst_local"], r["worst_local_hz"]))
    return aggs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("report")
    ap.add_argument("--vs", default=None, help="a second report, for an A/B of the decomposition")
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--only", default=None)
    ap.add_argument("--top", type=int, default=8)
    ap.add_argument("--png", default=None)
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    if args.selftest and not selftest():
        sys.exit(1)

    print("\n" + "=" * 104)
    print("FR AND THD AS CURVES -- residual = LEVEL + TILT + CURVATURE + LOCAL")
    print("=" * 104)
    print("  report : %s" % args.report)
    print("  bands  : %g - %g Hz (matrix_grade's own graded range)" % (GRADE_LO, GRADE_HI))
    print("  ⚠ `rms` here is the QUADRATIC mean over rows (needed for the four terms to partition")
    print("    the group total); matrix_grade's headline is the ARITHMETIC mean. Both printed.")
    print("  ⚠ LOCAL on a 1/3-octave grid is a LOWER BOUND on a narrow feature -- it says WHERE to")
    print("    look at full resolution, it does not measure the feature (session 46).")

    fs, rows = fr_rows(args.report, args.only)
    out = {"fr": report("FR  (plugin_dB - pedal_dB)", rows, args.top)}

    tfs, trows, tlevel = thd_rows(args.report, args.only)
    if trows:
        out["thd"] = report("THD (20log10 plugin%% / pedal%%) -- a RATIO, so decomposed in dB", trows,
                            args.top)
        print("\n  THD vs STIMULUS LEVEL -- the COMPRESSION curve, which no per-row aggregate holds.")
        print("  Mean THD error (dB) per sweep level; a TREND means the model's compression onset is")
        print("  wrong, a flat offset means its distortion amount is (session 57's reading (i)/(ii)).")
        # ⚠ Order by LEVEL, not alphabetically. Sorting the sweep names as strings gives
        # -12, -18, -6, so a "trend = last - first" would be -6 minus -12 -- neither the full
        # span nor the direction it claims. A trend statistic whose axis is mis-ordered is worse
        # than no trend statistic.
        def level_of(sw):
            try:
                return float(sw.rsplit("_", 1)[-1])
            except ValueError:
                return 0.0
        sweeps = sorted({sw for d in tlevel.values() for sw in d}, key=level_of)
        hdr = "  %-46s" % "row"
        for sw in sweeps:
            hdr += " %13s" % sw
        print(hdr + "     trend (hot - quiet)")
        shown = 0
        for f, d in sorted(tlevel.items(), key=lambda kv: -max(abs(v) for v in kv[1].values())):
            if len(d) < len(sweeps):
                continue
            line = "  %-46s" % f[:46]
            for s in sweeps:
                line += " %+13.2f" % d[s]
            line += "   %+.2f dB" % (d[sweeps[-1]] - d[sweeps[0]])   # hottest - quietest
            print(line)
            shown += 1
            if shown >= args.top:
                break

    if args.vs:
        _, rows_b = fr_rows(args.vs, args.only)
        print("\n" + "=" * 104)
        print("A/B -- which TERM moved? (a change that lowers rms by raising `local` is a")
        print("compensating error, and the total alone cannot show that)")
        print("=" * 104)
        shared = sorted(set(rows) & set(rows_b))
        print("  %d shared rows" % len(shared))
        print("  %-10s %9s %9s %9s" % ("term", "A", "B", "B - A"))
        for t in TERMS + ["rms"]:
            a = float(np.sqrt(np.mean([rows[k][t] ** 2 for k in shared])))
            b = float(np.sqrt(np.mean([rows_b[k][t] ** 2 for k in shared])))
            print("  %-10s %9.3f %9.3f %+9.3f" % (t, a, b, b - a))

    if args.png:
        try:
            import matplotlib
            matplotlib.use("Agg")
            import matplotlib.pyplot as plt
            fig, ax = plt.subplots(1, 2, figsize=(13, 5))
            for k, r in sorted(rows.items(), key=lambda kv: -kv[1]["local"])[:6]:
                ax[0].semilogx(fs, r["local_curve"], lw=1.3, label="%s %s" % (k[0][:22], k[1]))
            ax[0].set_title("LOCAL residual (smooth shape removed) -- narrow features only")
            ax[0].set_xlabel("Hz"); ax[0].set_ylabel("dB")
            ax[0].grid(True, which="both", alpha=0.3); ax[0].legend(fontsize=6)
            names = ["OD ex gain-n12", "OD gain-n12", "CLEAN", "ALL"]
            w, xs = 0.2, np.arange(len(names))
            for i, t in enumerate(TERMS):
                ax[1].bar(xs + i * w, [out["fr"][n][t] if out["fr"].get(n) else 0 for n in names],
                          w, label=t)
            ax[1].set_xticks(xs + 1.5 * w); ax[1].set_xticklabels(names, fontsize=8)
            ax[1].set_ylabel("dB rms"); ax[1].legend(fontsize=8)
            ax[1].set_title("Where the FR error lives, by group")
            ax[1].grid(True, axis="y", alpha=0.3)
            os.makedirs(os.path.dirname(args.png) or ".", exist_ok=True)
            fig.tight_layout(); fig.savefig(args.png, dpi=120)
            print("\n  wrote %s" % args.png)
        except ImportError:
            print("\n  (matplotlib not available -- no plot written)")

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        clean = {k: {kk: {t: v[t] for t in TERMS + ["rms", "n", "worst_local", "worst_local_hz"]}
                     for kk, v in d.items() if v} for k, d in out.items()}
        json.dump(clean, open(args.json, "w"), indent=1, default=float)
        print("  wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
