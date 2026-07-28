#!/usr/bin/env python3.11
"""A3 / ATTACK: extract the ATTACK network's LINEAR transfer, de-convolved from the clipper.

Every ATTACK number to date (sessions 55-57) is a DESCRIBING-function ratio: the pedal's ATTACK
blend ladders all sit at drive noon, so the measured boost/cut ratio is the linear network's
effect AFTER the clipper has partly compressed it away.  Session 57 could only read the
DIRECTION of the level trend and had to state that "the linear limit's magnitude is NOT pinned".
It scoped 6 drive-min captures as the way to pin it.

This tool pins it from the captures ALREADY ON DISK, with no model and no new data.

THE IDENTITY IT USES
  Write the OD path as  linear A(f) -> clipper -> linear B(f), and let the ATTACK switch insert
  a linear factor h(f) ahead of the clipper.  Under a swept sine the clipper sees ONE tone at a
  time, of amplitude |A(f)|.L, so its describing-function gain is a function of that one scalar:

      r_ref  (f, L) = |B.A| . n(|A|.L)
      r_boost(f, L) = |B.A| . h . n(h.|A|.L)      = h . r_ref(f, L + h)      [dB: L + h_dB]

  so                                     ratio_dB(f, L) = h_dB(f) + S_f(L + h_dB) - S_f(L)

  where S_f is the pedal's OWN ref transfer as a function of stimulus level.  h is then solved
  per band, per level, by bisection (the right-hand side is monotone in h, so the root is
  unique).  Nothing about the clipper is assumed except that it is memoryless enough for a
  describing function -- its shape, its rails and its drive dependence all cancel.

WHY THIS IS BETTER-CONDITIONED THAN THE RAW RATIO -- the bias cancels EXACTLY
  The blend axis returns r = sqrt(|g1|^2 + H), an UPPER bound inflated by harmonic power H
  (session 52 item 3b), and that inflation is worse at high level -- which is exactly where
  the ATTACK effect reads smallest.  Here it CANCELS: boost at level L and ref at level L+h
  present the clipper with the *identical* input waveform, so they carry the identical harmonic
  power, and the identity above equates those two measurements rather than a measurement to a
  model.  This is the first ATTACK instrument that is not exposed to that bias.

  ⚠ ONE SECOND-ORDER LEAK, stated rather than hidden: harmonics generated when the sweep is at
  f/2, f/3 ... land in the band at f.  In the boost condition those were generated at drive
  h(f/2).A(f/2).L, in the ref-at-(L+h(f)) condition at h(f).A(f/2).L.  These agree only where h
  is flat with frequency, so the residual leak scales with h's own SLOPE.  It is therefore
  smallest exactly for the throw that turns out to be flattest (CUT) and is reported, not
  assumed away.

GATES (all run before any number is read)
  * SELF-TEST: synthesise r_ref from a known compressive law and a known h(f), then recover h.
    A solver that cannot invert its own forward model cannot be read.
  * LIVENESS: h = 0 must come back as h = 0 at every band.
  * NO EXTRAPOLATION: L + h must land INSIDE the measured level range [-30, -6] dBFS.  Cells
    that would need level data we do not have are printed as "--", never silently extrapolated.
  * CONSISTENCY IS THE VERDICT: h(f) is solved independently at each level.  A genuine LINEAR
    element gives the SAME h(f) from every level; spread across levels is the error bar, and a
    systematic trend means the linear-element premise itself is wrong.

SCOPE
  * ATTACK is [ENG] -- the 3-way switch is not on our schematic at all, so h(f) is a
    specification for a topology PROPOSAL, not a disagreement with a drawn circuit.
  * Magnitude only; this axis has no phase.
  * h is placed ahead of the clipper because sessions 55-57 established the carrier is
    pre-clipper.  A post-clipper linear element would show NO level dependence at all, which
    the boost throw plainly does.

Usage:  python3.11 analysis/attack_linear_extract.py [--selftest]
"""
import argparse
import contextlib
import io
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a3_condition_axis as A            # noqa: E402
import a3_blend_axis as AX               # noqa: E402

TAKE_FLOOR_DB = 0.144
RATIO_FLOOR_DB = math.sqrt(2.0) * TAKE_FLOOR_DB
FIT_HI_HZ = 1700.0
NAMES = ["ref (drive noon)", "attack boost", "attack cut"]
LEVELS = [("sweep_clean", -30.0), ("sweep_drv_-18", -18.0),
          ("sweep_drv_-12", -12.0), ("sweep_drv_-6", -6.0)]
LMIN, LMAX = -30.0, -6.0


# ------------------------------------------------------------------- capture side
def solved(sweep):
    """{condition: {band: r_dB}} for all three ATTACK conditions at one stimulus level.

    Same code path as attack_topology_probe.pedal_ratios -- restricted to the bands identified
    in ALL THREE conditions, because an aggregate over different members is not a comparison
    (the session-49 item-7 trap).
    """
    A.SWEEP = sweep
    bands_all, caps = A.load_report(A.REPORT)
    sol, tt = {}, {}
    for name in NAMES:
        files, b1, _ = A.CONDITIONS[name]
        t = A.ladder(caps, bands_all, files, b1, "pedal_db")
        bd = [f for f in sorted(t) if f <= A.FIT_HI_HZ]
        with contextlib.redirect_stdout(io.StringIO()):
            Bint, _ = AX.fit_taper(t, bd, name[:12], False)
        sol[name], tt[name] = A.solve(t, bd, name, Bint), t
    out, cond = {}, {}
    for f in sorted(sol[NAMES[0]]):
        if f > FIT_HI_HZ or not all(sol[n].get(f, (0, 0, 0, False))[3] for n in NAMES):
            continue
        out[f] = {n: 20.0 * math.log10(sol[n][f][0]) for n in NAMES}
        # conditioning proxy: how close the blend ladder comes to a cancellation null. A band can
        # clear `identified` and still be poorly conditioned -- min|t| says how poorly.
        cond[f] = min(min(tt[n][f][1:]) for n in NAMES)
    return out, cond


# ------------------------------------------------------------------- the solve
def make_S(levels_db, r_db):
    """S_f(x): the pedal's own ref transfer vs stimulus level, piecewise-linear, NO extrapolation."""
    lv = np.asarray(levels_db, float)
    rr = np.asarray(r_db, float)
    order = np.argsort(lv)
    lv, rr = lv[order], rr[order]

    def S(x):
        if x < lv[0] - 1e-9 or x > lv[-1] + 1e-9:
            return None
        return float(np.interp(x, lv, rr))
    return S


def solve_h(ratio_db, L, S, lo=-24.0, hi=24.0):
    """Invert  ratio = h + S(L+h) - S(L)  for h.  Monotone in h => unique root; bisection."""
    base = S(L)
    if base is None:
        return None, "no ref at this level"

    def g(h):
        v = S(L + h)
        return None if v is None else h + v - base

    # widen the search only as far as the level data actually supports
    lo = max(lo, LMIN - L)
    hi = min(hi, LMAX - L)
    if hi - lo < 1e-6:
        return None, "level range gives no room"
    glo, ghi = g(lo), g(hi)
    if glo is None or ghi is None:
        return None, "endpoint outside level range"
    if not (min(glo, ghi) - 1e-9 <= ratio_db <= max(glo, ghi) + 1e-9):
        return None, "needs L%+.1f dB, outside captured levels" % (
            (hi if ratio_db > ghi else lo),)
    for _ in range(200):
        mid = 0.5 * (lo + hi)
        gm = g(mid)
        if gm is None:
            return None, "interior outside level range"
        if (gm - ratio_db) * (glo - ratio_db) <= 0:
            hi, ghi = mid, gm
        else:
            lo, glo = mid, gm
    return 0.5 * (lo + hi), ""


# ------------------------------------------------------------------- gates
def selftest():
    """Forward-model a known h(f) through a known compressor, then recover it."""
    print("=== SELF-TEST: recover a known h(f) through a known compressor ===")
    f = np.array([80., 101., 127., 160., 202., 254., 403., 508., 640., 1016., 1613.])
    A_f = 10 ** (-(0.6 * np.log10(f / 80.0)))          # a bass-tilted pre-clipper path
    truth = 3.0 + 5.0 * np.exp(-((np.log10(f / 200.0)) ** 2) / 0.18)   # a peaked h(f), +3..+8 dB

    def n_of(u):                                        # a soft compressor, gain vs amplitude
        return 1.0 / (1.0 + 0.9 * u)

    def r_ref_db(fi, L):
        u = A_f[fi] * 10 ** (L / 20.0)
        return 20.0 * math.log10(n_of(u) * A_f[fi])

    ok, worst, tested = True, 0.0, 0
    for fi in range(len(f)):
        S = make_S([lv for _, lv in LEVELS], [r_ref_db(fi, lv) for _, lv in LEVELS])
        for _, L in LEVELS:
            h = truth[fi]
            if L + h > LMAX or L + h < LMIN:
                continue                                # the tool refuses these cells too
            ratio = h + S(L + h) - S(L)
            got, why = solve_h(ratio, L, S)
            if got is None:
                print("    f=%.0f L=%+.0f  UNSOLVED (%s)" % (f[fi], L, why))
                ok = False
                continue
            worst = max(worst, abs(got - h))
            tested += 1
    print("  %d cells solved, worst |h_recovered - h_true| = %.2e dB   %s"
          % (tested, worst, "OK" if ok and worst < 1e-6 else "FAIL"))

    # liveness: an inert switch must return exactly zero
    dead = 0.0
    for fi in range(len(f)):
        S = make_S([lv for _, lv in LEVELS], [r_ref_db(fi, lv) for _, lv in LEVELS])
        for _, L in LEVELS:
            got, _ = solve_h(0.0, L, S)
            if got is not None:
                dead = max(dead, abs(got))
    print("  LIVENESS: h = 0 must come back as 0: worst %.2e dB   %s"
          % (dead, "OK" if dead < 1e-6 else "FAIL"))
    return ok and worst < 1e-6 and dead < 1e-6


# ------------------------------------------------------------------- main
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    args = ap.parse_args()
    gate = selftest()
    if args.selftest:
        sys.exit(0 if gate else 1)
    if not gate:
        print("\n  GATE FAILED -- stopping rather than printing numbers the solver cannot make.")
        sys.exit(1)

    per_level, cond_all = {}, {}
    for sw, L in LEVELS:
        try:
            per_level[L], cond_all[L] = solved(sw)
        except SystemExit:
            print("  (%s unavailable)" % sw)
    bands = sorted(set.intersection(*[set(d) for d in per_level.values()]))
    condmin = {f: min(cond_all[L][f] for L in per_level) for f in bands}
    print("\n=== INPUT: %d bands identified at every level, %.0f - %.0f Hz ==="
          % (len(bands), bands[0], bands[-1]))

    print("\n=== 0. THE REF TRANSFER's OWN LEVEL DEPENDENCE (what makes the solve possible) ===")
    print("  If this were flat, the clipper would be inert and ratio = h directly. Its total")
    print("  variation is the COMPRESSION BUDGET: the most level-dependence any pre-clipper")
    print("  linear h can borrow from the clipper at that band.")
    print("  %6s %s %10s %9s" % ("f Hz", "".join("%9.0f" % L for _, L in LEVELS),
                                 "budget dB", "min|t|"))
    for f in bands:
        r = [per_level[L][f][NAMES[0]] for _, L in LEVELS]
        print("  %6.0f %s %10.2f %9.3f"
              % (f, "".join("%9.2f" % v for v in r), max(r) - min(r), condmin[f]))
    print("  ⚠ This instrument's own weakness grows with frequency: harmonics generated when the")
    print("    sweep is at f/2, f/3 ... land in the band at f, and the OD path is bass-heavy, so")
    print("    the leak described in the header gets WORSE as f rises. Expect the residuals below")
    print("    to degrade with frequency for that reason alone, and do not read a refutation from")
    print("    a band where they do.")

    for throw, cond in (("BOOST", "attack boost"), ("CUT", "attack cut")):
        print("\n=== %s: the ATTACK network's LINEAR transfer h(f), solved at each level ==="
              % throw)
        print("  A linear element gives the SAME h(f) from every level. Spread = the error bar.")
        print("  %6s %s %10s %8s" % ("f Hz", "".join("%9.0f" % L for _, L in LEVELS),
                                     "mean h dB", "spread"))
        rows = []
        for f in bands:
            cells, vals = [], []
            for _, L in LEVELS:
                d = per_level[L][f]
                h, _why = solve_h(d[cond] - d[NAMES[0]], L, make_S(
                    [lv for _, lv in LEVELS], [per_level[lv][f][NAMES[0]] for _, lv in LEVELS]))
                if h is None:
                    cells.append("       --")
                else:
                    cells.append("%+9.2f" % h)
                    vals.append(h)
            if vals:
                rows.append((f, float(np.mean(vals)), max(vals) - min(vals), len(vals)))
                print("  %6.0f %s %+10.2f %8.2f%s"
                      % (f, "".join(cells), np.mean(vals), max(vals) - min(vals),
                         "" if len(vals) > 1 else "   (1 level only)"))
            else:
                print("  %6.0f %s %10s %8s" % (f, "".join(cells), "--", "--"))
        multi = [r for r in rows if r[3] > 1]
        if multi:
            sp = [r[2] for r in multi]
            print("  --- consistency over the %d bands solved at 2+ levels: mean spread %.2f dB, "
                  "worst %.2f dB (floor %.3f)" % (len(multi), float(np.mean(sp)), max(sp),
                                                  RATIO_FLOOR_DB))
            hs = [r[1] for r in multi]
            print("  --- h(f) range over those bands: %+.2f .. %+.2f dB, mean %+.2f"
                  % (min(hs), max(hs), float(np.mean(hs))))
        joint_fit(throw, cond, bands, per_level, condmin)
        budget_bound(throw, cond, bands, per_level)


def budget_bound(throw, cond, bands, per_level):
    """A FIT-FREE bound. The strongest form of the result, because nothing is optimised.

        ratio(L) = h + S(L+h) - S(L)   =>   |ratio(L1) - ratio(L2)| <= 2 . TV(S)

    where TV(S) is the total variation of the pedal's OWN ref transfer over the captured level
    range.  h drops out entirely.  So if the measured ratio swings by more than twice the
    band's compression budget, NO linear pre-clipper factor of ANY value can produce it --
    there is not enough compression at that band to borrow the level dependence from.

    Using the budget over the FULL captured range (rather than the sub-range h actually
    reaches) makes the bound generous, so exceeding it is decisive rather than marginal.
    """
    use = [-30.0, -18.0] if throw == "BOOST" else [-18.0, -12.0, -6.0]
    print("\n  --- %s: FIT-FREE BOUND -- measured swing vs 2 x the compression budget ---" % throw)
    print("  %6s %11s %10s %10s   %s" % ("f Hz", "swing dB", "2xbudget", "excess", "verdict"))
    decisive = []
    for f in bands:
        r = [per_level[L][f][NAMES[0]] for _, L in LEVELS]
        budget = 2.0 * (max(r) - min(r))
        rat = [per_level[L][f][cond] - per_level[L][f][NAMES[0]] for L in use]
        swing = max(rat) - min(rat)
        over = swing - budget
        tag = "IMPOSSIBLE for any linear h" if over > 0 else "within the budget"
        if over > 0:
            decisive.append((f, over))
        print("  %6.0f %11.2f %10.2f %+10.2f   %s" % (f, swing, budget, over, tag))
    if decisive:
        print("  --- %d band(s) exceed the bound: %s"
              % (len(decisive), ", ".join("%d Hz by %+.2f dB" % d for d in decisive)))
        print("      At these bands the pedal's own OD transfer barely compresses, yet the ATTACK")
        print("      effect moves several dB with level. No pre-clipper linear element can do that.")
    else:
        print("  --- no band exceeds the bound: the measured level dependence is entirely")
        print("      compatible with a linear pre-clipper element being compressed away.")


def joint_fit(throw, cond, bands, per_level, condmin):
    """ONE h per band for ALL levels at once -- the actual gate.

    The per-level table above shows the spread; this asks the falsifiable question directly:
    is there a SINGLE linear h(f) that reproduces the measured ratio at every level, given the
    pedal's own measured compression?  If yes the residual sits at the floor and the linear
    pre-clipper premise is confirmed.  If not, it is refuted, and the residual says by how much.

    The usable level subset is chosen by FEASIBILITY, not by taste: L + h must stay inside the
    captured level range, so a positive h drops the hottest rows and a negative h drops the
    quietest.  The subset and its degrees of freedom are printed, because a residual over 2
    points with 1 parameter is a weaker statement than one over 3 and must not be quoted as if
    it were the same.
    """
    levels = [L for _, L in LEVELS]
    # ⚠ ONE FIXED level subset per throw, chosen by FEASIBILITY, identical at every band.
    # Letting each band pick its own subset makes the residuals an aggregate over different
    # members, which is not a comparison (the session-49 item-7 / 52-item-1 trap). A positive h
    # pushes L+h past the hottest captured level, so BOOST can only use the two quiet rows; a
    # negative h pushes past the quietest, so CUT drops -30 and keeps three.
    use = [-30.0, -18.0] if throw == "BOOST" else [-18.0, -12.0, -6.0]
    hlo = max(LMIN - min(use), -20.0)
    hhi = min(LMAX - max(use), 20.0)
    print("\n  --- %s: ONE h per band, SAME %d levels at every band (the gate) ---"
          % (throw, len(use)))
    print("      levels %s dBFS, h restricted to [%+.1f, %+.1f] dB so L+h stays inside the"
          % ([int(x) for x in use], hlo, hhi))
    print("      captured range -- no extrapolation. %d point(s), 1 parameter => %d dof."
          % (len(use), len(use) - 1))
    print("  %6s %8s %9s %8s  %s"
          % ("f Hz", "h dB", "resid dB", "min|t|", "measured vs predicted"))
    resids, flagged = [], []
    for f in bands:
        S = make_S(levels, [per_level[L][f][NAMES[0]] for L in levels])
        meas = {L: per_level[L][f][cond] - per_level[L][f][NAMES[0]] for L in levels}
        grid = np.linspace(hlo, hhi, 16001)
        best = None
        for h in grid:
            err = [meas[L] - (h + S(L + h) - S(L)) for L in use]
            r = math.sqrt(float(np.mean(np.square(err))))
            if best is None or r < best[1]:
                best = (h, r)
        h, r = best
        rail = "*" if min(abs(h - hlo), abs(h - hhi)) < 1e-3 else " "
        if rail == "*":
            flagged.append(f)
        resids.append((f, r))
        pred = ", ".join("%+.1f/%+.1f" % (meas[L], h + S(L + h) - S(L)) for L in use)
        print("  %6.0f %+8.2f%s%8.3f %8.3f  %s" % (f, h, rail, r, condmin[f], pred))
    if flagged:
        print("      * h rests on its feasibility bound at %s Hz -- not identified there, the"
              % [int(x) for x in flagged])
        print("        captured level range simply does not reach that far.")
    rs = [r for _, r in resids]
    print("  --- residual: mean %.3f dB, worst %.3f dB over %d bands, floor %.3f"
          % (float(np.mean(rs)), max(rs), len(rs), RATIO_FLOOR_DB))
    lowf = [r for f, r in resids if f <= 202]
    print("  --- restricted to 80-202 Hz (best-conditioned, min|t| well clear of the null):"
          " mean %.3f dB, worst %.3f dB" % (float(np.mean(lowf)), max(lowf)))
    print("  --- VERDICT: %s"
          % ("a single linear pre-clipper h(f) EXPLAINS this throw"
             if max(rs) <= RATIO_FLOOR_DB else
             "NO single linear pre-clipper h(f) explains this throw across the full band "
             "(worst %.0fx floor); over 80-202 Hz it is %s"
             % (max(rs) / RATIO_FLOOR_DB,
                "within %.0fx" % (max(lowf) / RATIO_FLOOR_DB))))


if __name__ == "__main__":
    main()
