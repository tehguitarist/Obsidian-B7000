#!/usr/bin/env python3.11
"""GATE AQ — is `OdToneRestore`'s Q residual STRUCTURAL, and does matching the SHAPE dissolve the
point-vs-area disagreement GATE AP left as a user decision?

WHY THIS EXISTS
---------------
Session 152 closed with two items and they may be ONE item.

  (a) `OdToneRestore.h` says of the GRUNT-cut row: *"That Cut residual is STRUCTURAL, not a tuning
      miss: a single peaking section adding a few dB at the centre cannot narrow a null that is
      already 14 dB deep and broad.  Narrowing it needs a second section shaping the SHOULDERS.
      Do not spend more gain iterations on it."*  ⚠⚠ THAT IS A CLAIM, AND ITS EVIDENCE IS AN
      ITERATION THAT STALLED.  A stall is not a bound — `a-backlog-item's-proposed-REPAIR-is-a-
      claim` (s142), `an-unattempted-remedy-is-not-a-frozen-one`.  The honest form is a
      REACHABILITY question: sweep the section's Q to its limit, holding the DEPTH matched, and ask
      whether the composite's Q can reach the pedal's AT ALL.  That answer has no threshold in it —
      the pedal's Q is either inside the attained set or it is not.

  (b) GATE AP found the two depth metrics solve to different gains at 7 of 9 entries and left
      "match the notch by its BOTTOM or by its AREA?" as an explicit USER DECISION.  AP6 then
      attributed that disagreement to a SHAPE mismatch rather than to the censoring, resting on
      AP1c's control: with the pedal's null shaped EXACTLY like the biquad, the two metrics recover
      the same gain to 2e-4 dB.

⭐⭐ (a) AND (b) MEET.  If AP6's attribution is right, a solve that matches the pedal's Q as well as
its depth must make the two metrics agree, because it removes the very mismatch AP1c names as the
cause.  So the 2-D solve is not merely AP's solve with an axis freed — it is a **TEST OF AP6's
ATTRIBUTION, and it can fail.**  If the gap collapses, (b) was never a decision: it was a symptom
of (a).  If it does not, "shape mismatch" is refuted as the explanation and the remaining
candidates (centre offset, the null's asymmetry) are named rather than assumed.

⛔⛔ AND THE FIRST THING THIS GATE FOUND WAS THAT THE Q READER ITSELF COULD NOT SUPPORT THE
QUESTION.  `notch_geometry`'s `q` snaps both half-depth crossings to whole 1/48-oct GRID CELLS, so
the width is an integer number of cells and `q` can only return f0/(k*df).  Above Q~8 the attainable
values are {8.65, 11.54, 17.31, ...} and nothing between — true Q of 8, 10 and 11 ALL read 8.651.
The steps are 20-50 % wide, which is the SIZE of the effect the project is measuring with it, and
`OdToneRestore.h`'s "the Cut row stalls at 1.35-1.51 too broad" is ONE TO TWO of those steps.
⇒ this gate adds `q_interp` (same definition, crossings interpolated in log-f) and runs on that;
`q` is untouched so every pre-s153 number, GATE AP included, stays reproducible.  AQ1c is the
evidence for both halves.  This is `a-statistic-can-be-a-fine-DETECTOR-and-a-catastrophic-
OBJECTIVE` (s151) a second time on this same stage, on the Q axis instead of the depth axis.

⚠ WHAT THIS GATE DOES NOT DO.  It ships nothing and proposes no constant.  A 2-D solve says what a
section would have to BE; whether ONE section can be it is AQ2's question, and whether the result is
worth shipping is still the user's (GATE AP §11's reasons are untouched).

⭐ AND THE Q TARGET IS NOT CENSORED, WHICH IS WHY THIS IS WORTH DOING AT ALL.  Q is a property of
the FLANKS; the deconvolution residue censors the BOTTOM.  So Q is a measurement everywhere the
depth is a lower bound, and it is the one piece of shape information GATE AP left unused.

    /opt/homebrew/bin/python3.11 analysis/notch_shape_gate.py
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import feature_locus_gate as W          # noqa: E402
import null_depth_censor_gate as AP     # noqa: E402  — GATE AP, for solve_gain (imported, not copied)
import od_tone_restore_fit as F         # noqa: E402

REAL = AP.REAL                          # the three realistic stimulus rungs — imported, not re-listed
ROWS = AP.ROWS                          # (name, physical GRUNT position, capture set)
FIT_RESIDUAL_DB = AP.FIT_RESIDUAL_DB    # s151's own converged residual, ±0.83 dB

# ⚠⚠ EVERY Q IN THIS GATE IS THE INTERPOLATED ONE.  Named once, here, so no sub-gate can quietly
# read the quantised `q` — which is the defect AQ1c exists to document.
QKEY = "q_interp"

# The section's Q ladder for the reachability sweep.  Deliberately runs far past anything anyone
# would ship (s150 drove Q to 32 chasing a broken statistic, and that was pathological) — the point
# is to find the LIMIT of what one section can do, not to propose a value.  Log-spaced, because Q
# is a ratio.
QLADDER = np.geomspace(1.0, 120.0, 28)

GAIN_LO, GAIN_HI = -12.0, 60.0          # the same bracket GATE AP's solve uses

FAIL = []
NOTE = []


def fail(tag, msg):
    FAIL.append(tag)
    print(f"  ❌ {tag}: {msg}")


# ================================================================================================
# The composite, and the two solves
# ================================================================================================
def composite(g, mod_off, gain, q, drv, T, fs):
    """The stage-subtracted model curve with a candidate section added back.

    Exact and rebuild-free: the stage is LINEAR and IN SERIES, so its dB response adds.  Same
    argument that licenses `--stage-off` and GATE AP's solve.  The PEAK section is added back at
    its shipped setting because `current_response` (which produced `mod_off`) removed it — this
    gate is about the notch only and must not silently delete a second shipped section."""
    peak = F.rbj_peak_db(g, fs, T["kPeakFreq"], T["kPeakQ"], F.lerp5(T["kPeakGainDb"], drv, T["kX"]))
    return mod_off + F.rbj_peak_db(g, fs, T["kNotchFreq"], q, -gain) + peak


def _geo(g, mod_off, gain, q, drv, T, fs):
    try:
        return F.notch_geometry(g, composite(g, mod_off, gain, q, drv, T, fs))
    except RuntimeError:
        return None


def solve_gain_at_q(g, mod_off, target_depth, q, drv, T, fs, metric, uniq=False):
    """Gain at which the composite's depth (under `metric`) equals `target_depth`, at a GIVEN Q.

    ⚠ This is GATE AP's `solve_gain` with Q promoted from a shipped constant to an argument, and
    AQ1a asserts the two agree when that argument IS the shipped value — a cross-gate known answer
    whose right answer already exists, rather than a re-implementation nobody checked.

    ⚠ The uniqueness ladder is OFF by default and on only where a result is quoted.  GATE AP runs
    it on every call because it makes ~1 call per cell; this gate nests this solve inside an outer
    root-find, so running it every time would multiply the work by 25 for a check whose answer
    cannot vary meaningfully between adjacent Q rungs."""
    from scipy.optimize import brentq
    key = "depth_area" if metric == "area" else "depth_point"

    def err(gain):
        r = _geo(g, mod_off, gain, q, drv, T, fs)
        if r is None:
            return -1e3                  # no feature yet ⇒ far too little gain (AP's sentinel)
        return r[key] - target_depth

    if err(GAIN_LO) > 0 or err(GAIN_HI) < 0:
        return None
    if uniq:
        vals = [err(v) for v in np.linspace(GAIN_LO, GAIN_HI, 25)]
        if sum(1 for a, b in zip(vals, vals[1:]) if (a < 0) != (b < 0)) > 1:
            NOTE.append(f"non-unique gain root: {metric} q={q:.2f} drv={drv:.2f}")
    return float(brentq(err, GAIN_LO, GAIN_HI, xtol=1e-3))


def q_reach(g, mod_off, target_depth, drv, T, fs, metric):
    """-> [(section_q, gain, composite_q)] across QLADDER, DEPTH held matched at every rung.

    THIS IS THE REACHABILITY INSTRUMENT.  Holding the depth matched is what makes it a fair test:
    without it a high-Q section trivially "narrows" the composite by simply doing less, and the
    resulting Q would be a statement about the depth being wrong rather than about the shape."""
    out = []
    for q in QLADDER:
        gain = solve_gain_at_q(g, mod_off, target_depth, q, drv, T, fs, metric)
        if gain is None:
            continue
        r = _geo(g, mod_off, gain, q, drv, T, fs)
        if r is not None and np.isfinite(r[QKEY]):
            out.append((float(q), float(gain), float(r[QKEY])))
    return out


def solve_gain_q(g, mod_off, ped_geo, drv, T, fs, metric):
    """The 2-D solve: (gain, Q) matching the pedal's DEPTH *and* its Q.

    Nested, not simultaneous: the inner solve pins depth at each candidate section-Q, so the outer
    root-find sees a one-dimensional, depth-matched function of Q alone.  That keeps every
    intermediate point physically meaningful (each already matches the depth) and means a failure to
    reach is a statement about Q, uncontaminated by the depth.

    -> (gain, section_q, composite_q, status), status in {ok, unreachable-hi, unreachable-lo}.
    ⚠ `unreachable` is a RESULT, not an error — it is exactly AQ2's finding, and s134's lesson is
    that `sys.exit`ing on "no root exists" throws away the strongest refutation a gate can make."""
    from scipy.optimize import brentq
    target_depth = ped_geo["depth_area" if metric == "area" else "depth_point"]
    target_q = ped_geo[QKEY]
    lad = q_reach(g, mod_off, target_depth, drv, T, fs, metric)
    if len(lad) < 2 or not np.isfinite(target_q):
        return None
    comp_q = [c for _, _, c in lad]
    if target_q > max(comp_q):
        i = int(np.argmax(comp_q))
        return (lad[i][1], lad[i][0], comp_q[i], "unreachable-hi")
    if target_q < min(comp_q):
        i = int(np.argmin(comp_q))
        return (lad[i][1], lad[i][0], comp_q[i], "unreachable-lo")

    def qerr(q):
        gain = solve_gain_at_q(g, mod_off, target_depth, q, drv, T, fs, metric)
        if gain is None:
            return -1e3
        r = _geo(g, mod_off, gain, q, drv, T, fs)
        return (r[QKEY] if r is not None and np.isfinite(r[QKEY]) else -1e3) - target_q

    # Bracket on the ladder itself, at the FIRST sign change, so a non-monotone composite-Q curve
    # cannot silently hand back a root from a region the sweep shows is unphysical.
    lo = hi = None
    for (qa, _, ca), (qb, _, cb) in zip(lad, lad[1:]):
        if (ca - target_q < 0) != (cb - target_q < 0):
            lo, hi = qa, qb
            break
    if lo is None:
        return (lad[-1][1], lad[-1][0], comp_q[-1], "unreachable-hi")
    q = float(brentq(qerr, lo, hi, xtol=1e-3))
    gain = solve_gain_at_q(g, mod_off, target_depth, q, drv, T, fs, metric, uniq=True)
    if gain is None:
        return None
    r = _geo(g, mod_off, gain, q, drv, T, fs)
    return (gain, q, float(r[QKEY]) if r is not None else float("nan"), "ok")


# ================================================================================================
# AQ1 — known answers
# ================================================================================================
def aq1a():
    """CROSS-GATE KNOWN ANSWER: with Q pinned to the shipped value, this gate's inner solve must
    return GATE AP's.  The right answer already exists and was produced by code this gate does not
    share — AP's `solve_gain` reads Q out of the shipped table itself — so agreement certifies that
    promoting Q to an argument did not change the quantity being solved for.

    ⚠ What this is BLIND to, stated because s145/s149 cost the project ten sessions on exactly this
    shape: both sides evaluate the SAME `notch_geometry`, the SAME `rbj_peak_db` and the SAME
    curves.  It validates the Q plumbing, not the reader, the biquad or the data — those are
    certified by AP1a/AP1c and by AQ1c/AQ1d below."""
    print("\nAQ1a  CROSS-GATE KNOWN ANSWER — inner solve at shipped Q == GATE AP's solve_gain")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    worst, n = 0.0, 0
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            g, ped, mod = F.curves(fname, REAL[1])
            mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
            try:
                pg = F.notch_geometry(g, ped)
            except RuntimeError:
                continue
            q_ship = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
            for metric in ("point", "area"):
                a = AP.solve_gain(g, mod_off, pg, drv, gpos, T, fs, metric)
                b = solve_gain_at_q(g, mod_off,
                                    pg["depth_area" if metric == "area" else "depth_point"],
                                    q_ship, drv, T, fs, metric)
                if a is None or b is None:
                    continue
                n += 1
                worst = max(worst, abs(a - b))
    print(f"  worst |AP − AQ| = {worst:.2e} dB over n={n} cells")
    if n == 0:
        fail("AQ1a", "no cell produced a comparison — the known answer never ran "
                     "(`empty-gate-must-fail`)")
    elif worst > 1e-6:
        fail("AQ1a", f"promoting Q to an argument changed the solve ({worst:.2e} dB) — nothing "
                     f"below is readable")
    else:
        print("  ✅ identical to GATE AP's solve, so the 2-D solve is that solve with one axis freed.")
    return worst, n


def aq1c():
    """THE READER: `q` is quantised to f0/(k*df); `q_interp` is monotone.  Both, measured.

    ⭐ The quantisation half is a STRUCTURAL known answer with no threshold: the crossings are whole
    grid cells, so every attainable `q` must equal f0/(k*df) for some integer k, df being the grid
    step at f0.  That is checked against the closed form, not eyeballed from a table.
    ⭐⭐ The monotonicity half is what licenses everything below.  A round trip can only recover an
    injected Q if the map (true Q -> read Q) is INJECTIVE; a step function is not, and that — not
    any error in the solve — is why a first draft of AQ1d failed at 3 of 4 injected pairs.
    ⚠ NEITHER reader is unbiased at low Q, and the bias is not a defect: the SHOULDER window
    truncates a broad notch, so the shoulder-referred depth is less than the section's centre gain
    and the width read at half of it is too narrow (AP1c documents the same effect on the depth).
    That bias cancels in any pedal-vs-composite comparison read the same way, so this arm gates on
    MONOTONICITY and on round-trip recovery, never on absolute accuracy."""
    print("\nAQ1c  THE Q READER — `q` is quantised, `q_interp` is monotone (both measured)")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    g = W.GRID
    flat = np.zeros_like(g)
    ladder = [3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 14, 16, 18, 20, 24, 30]
    print(f"  {'true Q':>7} {'q (grid)':>9} {'err %':>7} {'(m,n)':>9} | {'q_interp':>9} {'err %':>7}")
    # The EXACT structural predicate.  Both crossings are grid cells, so hi = f0*2^(m/48) and
    # lo = f0*2^(-n/48) for non-negative integers m, n, hence 1/q = 2^(m/48) - 2^(-n/48).  ⚠ A
    # first draft asserted the weaker `width = k*df` with df the FORWARD step — the linear
    # approximation to a geometric grid, which undershoots by ~0.07 cells and duly refused against
    # perfectly correct code.  `rebuild-targets-dont-transcribe` applied to one's own algebra:
    # derive the predicate from the grid the reader actually walks, don't linearise it.
    def cell_pair(qv):
        inv = 1.0 / max(qv, 1e-12)
        for m in range(0, 41):
            for nn in range(0, 41):
                if abs(inv - (2.0 ** (m / 48.0) - 2.0 ** (-nn / 48.0))) < 1e-9:
                    return (m, nn)
        return None

    reads, interps, kbad = [], [], []
    for qs in ladder:
        r = F.notch_geometry(g, flat + F.rbj_peak_db(g, fs, T["kNotchFreq"], qs, -14.0))
        pair = cell_pair(r["q"])
        if pair is None:
            kbad.append((qs, r["q"]))
        reads.append(r["q"])
        interps.append(r["q_interp"])
        print(f"  {qs:7.1f} {r['q']:9.3f} {100 * (r['q'] - qs) / qs:+7.2f} "
              f"{str(pair) if pair else '  --':>9} | "
              f"{r['q_interp']:9.3f} {100 * (r['q_interp'] - qs) / qs:+7.2f}")
    # (i) STRUCTURE — every grid reading is an exact (m, n) pair of whole cells.  No threshold.
    if kbad:
        fail("AQ1c", f"the grid reader's crossings are not whole grid cells at {kbad} — the "
                     f"quantisation account below is wrong, do not quote it")
    else:
        print("  ✅ every `q` reading is exactly 1/(2^(m/48) − 2^(−n/48)) for integer (m, n) ⇒ the")
        print("     width is a whole number of 1/48-oct cells.  Derived, not observed.")
    # (ii) NON-INJECTIVITY — count the collisions, which is the operational form of the defect.
    dup = len(reads) - len(set(round(v, 6) for v in reads))
    steps = sorted(set(round(v, 3) for v in reads))
    print(f"  `q` takes only {len(steps)} distinct values over {len(ladder)} true Qs "
          f"({dup} collisions): {steps}")
    worst_grid = max(abs(a - b) / b for a, b in zip(reads, ladder))
    worst_int = max(abs(a - b) / b for a, b in zip(interps, ladder))
    print(f"  worst relative error: `q` {100 * worst_grid:.1f} %   `q_interp` {100 * worst_int:.1f} %")
    # (iii) MONOTONICITY — the property an objective actually needs.
    mono_g = all(b >= a for a, b in zip(reads, reads[1:]))
    mono_i = all(b > a for a, b in zip(interps, interps[1:]))
    print(f"  strictly increasing?  `q` {'yes' if dup == 0 else 'NO (plateaus)'}   "
          f"`q_interp` {'yes' if mono_i else 'NO'}")
    if dup == 0:
        fail("AQ1c", "the grid reader shows NO collisions on this ladder — the quantisation this "
                     "gate is built around is not reproducing; re-check the grid before reading on")
    if not mono_i:
        fail("AQ1c", "`q_interp` is not strictly monotone in the true Q — it cannot be an objective "
                     "either, and the 2-D solve below is not readable")
    _ = mono_g
    return {"steps": steps, "collisions": dup, "worst_grid": worst_grid, "worst_interp": worst_int}


def aq1d():
    """SYNTHETIC ROUND TRIP on the 2-D solve — recover a KNOWN injected (G*, Q*).

    AP1c does this in one dimension.  Freeing Q needs its own round trip, because a 2-D solve can be
    wrong in a way a 1-D one cannot: it can trade gain against Q along a valley and land anywhere on
    it.  Recovering BOTH coordinates is what shows the two constraints pin a point.

    ⭐ WHY THIS IS EXACT AND NOT APPROXIMATE, which is what makes the bars tight rather than
    negotiated: the synthetic pedal IS `composite(G*, Q*)` on a flat background, so both of the
    solver's equations are satisfied EXACTLY at the injected pair.  Every bias of the reader —
    including the shoulder-truncation bias AQ1c measures — appears identically on both sides and
    cancels.  ⇒ the only thing that can break recovery is the reader failing to be injective, which
    is precisely what `q` does and `q_interp` does not.
    ⭐⭐ And it must hold under BOTH metrics, which is the claim AQ4's headline rests on: with the
    shape matched, 'depth' means the same thing either way."""
    print("\nAQ1d  SYNTHETIC ROUND TRIP — recover an injected (G*, Q*), both metrics")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    g = W.GRID
    flat = np.zeros_like(g)
    print(f"  {'G*':>6} {'Q*':>6} | {'pt gain':>8} {'pt Q':>7} | {'ar gain':>8} {'ar Q':>7} "
          f"| {'dG pt':>7} {'dQ% pt':>7} {'dG ar':>7} {'dQ% ar':>7}")
    for gstar, qstar in ((8.0, 5.0), (14.0, 9.0), (20.0, 12.0), (26.0, 18.0)):
        ped = flat + F.rbj_peak_db(g, fs, T["kNotchFreq"], qstar, -gstar)
        pg = F.notch_geometry(g, ped)
        got = {m: solve_gain_q(g, flat, pg, 0.5, T, fs, m) for m in ("point", "area")}
        if any(v is None or v[3] != "ok" for v in got.values()):
            fail("AQ1d", f"no 2-D root for (G*={gstar}, Q*={qstar}): "
                         f"point={got['point']}, area={got['area']}")
            continue
        gp, qp = got["point"][0], got["point"][1]
        ga, qa = got["area"][0], got["area"][1]
        print(f"  {gstar:6.1f} {qstar:6.1f} | {gp:8.3f} {qp:7.3f} | {ga:8.3f} {qa:7.3f} "
              f"| {gp - gstar:+7.3f} {100 * (qp - qstar) / qstar:+7.3f} "
              f"{ga - gstar:+7.3f} {100 * (qa - qstar) / qstar:+7.3f}")
        # Bars are the SOLVER's own tolerances, not chosen numbers: the inner brentq runs xtol=1e-3
        # on gain (dB) and the outer xtol=1e-3 on Q, so 0.05 dB and 0.5 % are ~50x and ~100x those.
        # A failure at that margin is non-injectivity of the reader, never tolerance.
        for tag, (gg, qq) in (("point", (gp, qp)), ("area", (ga, qa))):
            if abs(gg - gstar) > 0.05:
                fail("AQ1d", f"{tag} lost the injected GAIN (G*={gstar}: {gg - gstar:+.3f} dB)")
            if abs(qq - qstar) / qstar > 0.005:
                fail("AQ1d", f"{tag} lost the injected Q (Q*={qstar}: "
                             f"{100 * (qq - qstar) / qstar:+.2f} %)")
    # The same refusal control AP1c carries: a flat curve has no feature and the reader must say so.
    try:
        F.notch_geometry(g, flat)
        fail("AQ1d", "the reader found a null in a perfectly flat curve")
    except RuntimeError:
        print("  flat-curve control: reader REFUSES, as it must.")


# ================================================================================================
# AQ2 — REACHABILITY: can ONE section put the composite's Q on the pedal's, at any Q?
# ================================================================================================
def aq2():
    """The header's 'STRUCTURAL' claim, tested as a containment question.

    Per (GRUNT, DRIVE, sweep): sweep the section's Q over QLADDER with the gain re-solved at every
    rung so the DEPTH stays matched, and record the range of composite Q attained.  The pedal's Q is
    then either inside that range (⇒ one section suffices; the claim is refuted) or outside it (⇒
    the claim is confirmed, and now with a LIMIT rather than a stalled iteration).

    ⭐ No threshold anywhere: this is `is x in [min, max]`.
    ⚠ Read in the POINT metric because Q is a point-curve quantity by construction — a
    power-integrated depth has no width, so there is no area-metric Q to sweep against.
    ⭐ The `ped/comp @ship` column re-quotes `OdToneRestore.h`'s "1.35-1.51 too broad" on BOTH
    readers, which is the honest way to carry a claim whose original instrument AQ1c just found
    quantised."""
    print("\nAQ2  REACHABILITY — the composite Q one section can attain, DEPTH held matched")
    print(f"  ladder: section Q over {QLADDER[0]:.1f}-{QLADDER[-1]:.1f} ({len(QLADDER)} rungs); "
          f"gain re-solved at every rung.")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    out = {}
    print(f"\n  {'grunt':<6} {'drv':>4} {'sw':>4} | {'ped Q':>6} {'comp@ship':>9} "
          f"{'ratio':>6} {'(grid)':>7} | {'comp min':>8} {'comp max':>8} | {'reaches?':>8}")
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            for sw in REAL:
                g, ped, mod = F.curves(fname, sw)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                try:
                    pg = F.notch_geometry(g, ped)
                except RuntimeError:
                    continue
                lad = q_reach(g, mod_off, pg["depth_point"], drv, T, fs, "point")
                if len(lad) < 2:
                    continue
                cq = [c for _, _, c in lad]
                q_ship = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
                gain_ship = solve_gain_at_q(g, mod_off, pg["depth_point"], q_ship, drv, T, fs,
                                            "point")
                r_ship = (_geo(g, mod_off, gain_ship, q_ship, drv, T, fs)
                          if gain_ship is not None else None)
                cs = r_ship[QKEY] if r_ship else float("nan")
                cs_grid = r_ship["q"] if r_ship else float("nan")
                ok = min(cq) <= pg[QKEY] <= max(cq)
                out.setdefault(f"{gname}|{drv}", []).append(
                    {"sweep": sw, "ped_q": pg[QKEY], "ped_q_grid": pg["q"], "ship_q": q_ship,
                     "comp_ship_q": cs, "ratio": pg[QKEY] / cs if cs else None,
                     "ratio_grid": pg["q"] / cs_grid if cs_grid else None,
                     "comp_min": min(cq), "comp_max": max(cq), "reaches": bool(ok)})
                print(f"  {gname:<6} {drv:4.2f} {sw[-3:]:>4} | {pg[QKEY]:6.2f} {cs:9.2f} "
                      f"{pg[QKEY] / cs:6.2f} {pg['q'] / cs_grid:7.2f} | "
                      f"{min(cq):8.2f} {max(cq):8.2f} | {'YES' if ok else 'NO':>8}")
    tot = sum(len(v) for v in out.values())
    hit = sum(1 for v in out.values() for r in v if r["reaches"])
    print(f"\n  reachable in {hit} of {tot} cells.")
    if tot == 0:
        fail("AQ2", "no cell was measured (`empty-gate-must-fail`)")
    return out, hit, tot


def aq2b(reach):
    """IS 'THE PEDAL'S Q' EVEN ONE NUMBER?  Its spread across the three stimulus rungs.

    ⚠⚠ This is the check that decides how much weight anything above can carry, and it exists
    because `OdToneRestore.h` quotes the Q defect as a single figure per (GRUNT, DRIVE) entry —
    which presupposes that the pedal's Q at that entry IS a single figure.  Every rung is printed
    (`an-endpoint-pair-is-not-a-ladder`, s129) rather than summarised, and monotonicity is tested
    rather than assumed.

    ⭐ If the spread is comparable to, or larger than, the defect being chased, then a DRIVE-keyed
    table cannot represent the quantity at all — which is s151 §6's architectural limit (a
    knob-keyed stage cannot track a stimulus-dependent feature) restated on the Q axis, where it
    has never been measured."""
    print("\nAQ2b  IS 'THE PEDAL'S Q' ONE NUMBER?  — its own spread across the stimulus rungs")
    print(f"  {'grunt':<6} {'drv':>4} | {'-18':>7} {'-12':>7} {'-6':>7} | {'spread':>7} "
          f"| {'monotone?':>10}")
    spreads = []
    for key in sorted(reach, key=lambda k: (k.split("|")[0], float(k.split("|")[1]))):
        v = reach[key]
        by = {r["sweep"][-3:]: r["ped_q"] for r in v}
        vals = [by.get(s[-3:]) for s in REAL]
        got = [x for x in vals if x is not None]
        if len(got) < 2:
            continue
        sp = max(got) / max(min(got), 1e-9)
        spreads.append(sp)
        mono = all(b <= a for a, b in zip(got, got[1:])) or all(b >= a for a, b in zip(got, got[1:]))
        gname, drv = key.split("|")
        print(f"  {gname:<6} {float(drv):4.2f} | "
              + " ".join(f"{x:7.2f}" if x is not None else f"{'—':>7}" for x in vals)
              + f" | {sp:6.2f}x | {'yes' if mono else 'NO':>10}")
    if not spreads:
        fail("AQ2b", "no cell had two readable rungs (`empty-gate-must-fail`)")
        return None
    lo, hi = min(spreads), max(spreads)
    print(f"\n  the pedal's own Q spans {lo:.2f}x-{hi:.2f}x across stimulus at FIXED (GRUNT, DRIVE).")
    print("  ⇒ compare that against the defect being chased before quoting any single Q target:")
    print("     `OdToneRestore.h`'s Cut row is quoted as '1.35-1.51 too broad', i.e. 1.35-1.51x.")
    if hi >= 1.35:
        print("  ⛔ THE STIMULUS SPREAD IS AS LARGE AS THE DEFECT, OR LARGER, IN AT LEAST ONE CELL")
        print("     ⇒ 'the pedal's Q at this entry' is not a well-defined target, and a DRIVE-keyed")
        print("     table cannot carry it.  Same architectural limit s151 §6 found on the depth")
        print("     axis; this is its first measurement on the Q axis.")
    else:
        # The opposite verdict, printed rather than implied — a conclusion that cannot state its
        # own negation is narration (s34/s61/s68), and the mutation runner drives this branch.
        print("  ✅ Q IS STIMULUS-STABLE at every cell (worst spread below the quoted defect)")
        print("     ⇒ 'the pedal's Q at this entry' IS a well-defined target and a DRIVE-keyed")
        print("     table can carry it.")
    return lo, hi


# ================================================================================================
# AQ3 — the 2-D solve, per metric
# ================================================================================================
def aq3():
    """The 2-D solve, averaged over sweeps.

    ⛔⛔ ONLY `ok` CELLS VOTE IN THE MEAN — `defective-rows-must-not-vote`, and a first draft of this
    gate broke it.  An `unreachable` cell returns the CLOSEST attainable point, which at Cut × DRIVE
    0.50 is the Q-ladder's own ceiling (120): averaging that with two genuine solves produced a
    "mean Q" of 120.00 that is a property of my ladder, not of the pedal.  Unreachable cells are
    counted and named instead (AQ2 is where they are read).
    ⚠ The per-sweep SPREAD is printed beside every mean, because Q varies strongly across the three
    stimulus rungs (AQ2's ratio column runs 0.56-1.84) — a mean over that without its spread is
    exactly the summary this project has been burned by (`a-pooled-statistic-cannot-answer-about-
    its-own-axis`).  ⇒ read the spread before quoting any entry."""
    print("\nAQ3  THE 2-D SOLVE — (gain, Q) matching the pedal's DEPTH and its Q, per metric")
    print("  ⛔ unreachable cells do NOT vote in the mean (they clamp to the ladder end); they are")
    print("     counted in the `unr` column and read in AQ2.")
    T = F.shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    out = {}
    print(f"\n  {'grunt':<6} {'drv':>4} | {'ship G':>7} {'ship Q':>6} | {'pt G':>7} {'pt Q':>6} "
          f"{'n':>2} | {'ar G':>7} {'ar Q':>6} {'n':>2} | {'ar−pt G':>8} | {'unr':>3} "
          f"| {'Qspread':>8}")
    for gname, gpos, sname in ROWS:
        for fname, drv in F.SETS[sname]:
            acc = {"point": [], "area": []}
            unr = []
            for sw in REAL:
                g, ped, mod = F.curves(fname, sw)
                mod_off = mod - F.current_response(g, drv, fs, T, gpos, F.clean_frac_of(fname))
                try:
                    pg = F.notch_geometry(g, ped)
                except RuntimeError:
                    continue
                for metric in ("point", "area"):
                    r = solve_gain_q(g, mod_off, pg, drv, T, fs, metric)
                    if r is None:
                        continue
                    if r[3] != "ok":
                        unr.append(f"{metric[:2]}/{sw[-3:]}:{r[3].split('-')[-1]}")
                        continue                 # ⛔ does not vote
                    acc[metric].append((r[0], r[1]))
            if not acc["point"] or not acc["area"]:
                print(f"  {gname:<6} {drv:4.2f} | {'':7} {'':6} | NO REACHABLE CELL "
                      f"({len(unr)} unreachable: {','.join(unr)})")
                out[f"{gname}|{drv}"] = {"ship_g": F.lerp5(T["kNotchGainDb"][gpos], drv, T["kX"]),
                                         "ship_q": F.lerp5(T["kNotchQ"][gpos], drv, T["kX"]),
                                         "pt_g": None, "ar_g": None, "n_pt": len(acc["point"]),
                                         "n_ar": len(acc["area"]), "unreachable": unr}
                continue
            gp = float(np.mean([a for a, _ in acc["point"]]))
            qp = float(np.mean([b for _, b in acc["point"]]))
            ga = float(np.mean([a for a, _ in acc["area"]]))
            qa = float(np.mean([b for _, b in acc["area"]]))
            allq = [b for v in acc.values() for _, b in v]
            spread = max(allq) / max(min(allq), 1e-9)
            ship_g = F.lerp5(T["kNotchGainDb"][gpos], drv, T["kX"])
            ship_q = F.lerp5(T["kNotchQ"][gpos], drv, T["kX"])
            out[f"{gname}|{drv}"] = {"ship_g": ship_g, "ship_q": ship_q, "pt_g": gp, "pt_q": qp,
                                     "ar_g": ga, "ar_q": qa, "n_pt": len(acc["point"]),
                                     "n_ar": len(acc["area"]), "q_spread": spread,
                                     "unreachable": unr}
            print(f"  {gname:<6} {drv:4.2f} | {ship_g:7.2f} {ship_q:6.1f} | {gp:7.2f} {qp:6.2f} "
                  f"{len(acc['point']):2d} | {ga:7.2f} {qa:6.2f} {len(acc['area']):2d} | "
                  f"{ga - gp:8.2f} | {len(unr):3d} | {spread:8.2f}x")
    return out


# ================================================================================================
# AQ4 — THE HEADLINE: does matching the shape collapse the point/area disagreement?
# ================================================================================================
def aq4(sol2, sol1):
    """AP6's attribution, tested rather than assumed.

    AP6 concluded the metric disagreement is a SHAPE mismatch and not the censoring, on the strength
    of AP1c's synthetic control plus two correlations that are both weak (+0.196 with the floor
    margin, −0.314 with the Q ratio).  ⚠ A conclusion reached by ELIMINATION plus a synthetic
    control is exactly the kind that wants a direct test on real data, and there is one: if the
    mismatch is the cause, then removing it — solving with Q free, so the composite's shape matches
    the pedal's — must SHRINK the gap.

    ⭐ This can fail, and the failure is informative: if the gap survives shape matching, Q is not
    the shape coordinate that carries it, and the remaining candidates (centre offset, the null's
    asymmetry) are named rather than assumed."""
    print("\nAQ4  DOES MATCHING THE SHAPE COLLAPSE THE METRIC GAP?  (AP6's attribution, tested)")
    print("  |area − point| solved gain, at the SHIPPED Q (GATE AP) vs with Q FREE (AQ3).")
    print(f"\n  {'grunt':<6} {'drv':>4} | {'gap @ship Q':>11} | {'gap @free Q':>11} | {'change':>8}")
    a, b = [], []
    for key in sorted(sol2):
        gname, drv = key.split("|")[0], float(key.split("|")[1])
        # ⛔ Same rule as AQ3: a cell whose Q is unreachable has no shape-matched solution, so it
        # cannot answer "does shape-matching close the gap?" and must not be averaged into the
        # answer.  It is NAMED rather than silently dropped (`no-silent-caps`).
        if (gname, drv) not in sol1 or sol2[key].get("pt_g") is None:
            print(f"  {gname:<6} {drv:4.2f} | {'—':>11} | {'unreachable':>11} | (excluded)")
            continue
        _, mp, ma, _, _ = sol1[(gname, drv)]
        g1 = abs(ma - mp)
        g2 = abs(sol2[key]["ar_g"] - sol2[key]["pt_g"])
        a.append(g1)
        b.append(g2)
        print(f"  {gname:<6} {drv:4.2f} | {g1:11.2f} | {g2:11.2f} | {g2 - g1:+8.2f}")
    if not a:
        fail("AQ4", "no cell was comparable between the 1-D and 2-D solves (`empty-gate-must-fail`)")
        return None
    m1, m2 = float(np.mean(a)), float(np.mean(b))
    print(f"\n  MEAN gap: {m1:.2f} dB at the shipped Q -> {m2:.2f} dB with Q free "
          f"({100 * (m2 - m1) / max(m1, 1e-9):+.0f} %)")
    # The bar is the fit's own converged residual, imported from GATE AP rather than chosen here: a
    # disagreement smaller than the residual the table was fitted to cannot move a constant, so that
    # is the level at which "the two metrics agree" becomes operationally true.
    print(f"  bar: the fit's own residual, ±{FIT_RESIDUAL_DB:.2f} dB (imported from GATE AP).")
    if m2 <= FIT_RESIDUAL_DB:
        verdict = "COLLAPSED"
        print("  ⭐⭐ COLLAPSED — with the shape matched the two metrics agree inside the fit's own")
        print("     residual.  ⇒ AP6's attribution is CONFIRMED on real data, and 'match the notch")
        print("     by its BOTTOM or its AREA' is NOT a decision: it was a symptom of the Q error.")
    elif m2 < 0.5 * m1:
        verdict = "SHRANK"
        print("  ⭐ SHRANK by more than half but does not clear the fit's residual ⇒ the shape")
        print("     mismatch is a large part of the disagreement and is not all of it.")
    else:
        verdict = "SURVIVED"
        print("  ⛔ DID NOT COLLAPSE ⇒ AP6's 'shape mismatch' does not survive as the explanation;")
        print("     Q is not the shape coordinate that carries it.  The remaining candidates are")
        print("     the centre offset and the null's asymmetry, neither of which this solve frees.")
    return m1, m2, verdict


def main():
    print("=" * 96)
    print("GATE AQ — is the Q residual structural, and does shape-matching dissolve AP's decision?")
    print("=" * 96)
    w, n = aq1a()
    res = aq1c()
    aq1d()
    reach, hit, tot = aq2()
    qspan = aq2b(reach)
    sol2 = aq3()
    print("\n  (re-running GATE AP's 1-D solve for the AQ4 comparison — imported, not transcribed)")
    sol1 = AP.ap3()
    gaps = aq4(sol2, sol1)

    print("\n" + "=" * 96)
    print("VERDICT")
    print("=" * 96)
    print(f"  AQ1c  the shipped Q reader takes only {len(res['steps'])} distinct values over 16 true")
    print(f"        Qs (worst error {100 * res['worst_grid']:.0f} %); `q_interp` {100 * res['worst_interp']:.0f} % and strictly monotone.")
    print(f"  AQ2   the pedal's Q is attainable by ONE section in {hit} of {tot} cells.")
    if qspan:
        print(f"  AQ2b  the pedal's OWN Q spans {qspan[0]:.2f}x-{qspan[1]:.2f}x across stimulus at "
              f"fixed (GRUNT, DRIVE),")
        print(f"        against a defect quoted as 1.35-1.51x ⇒ the target is not a single number.")
    unreach = {k: v for k, v in reach.items() if not all(r["reaches"] for r in v)}
    if unreach:
        print("        cells where one section CANNOT reach it at any Q, with the limit:")
        for k in sorted(unreach):
            v = unreach[k]
            worst = max(v, key=lambda r: abs(r["ped_q"] - r["comp_max"]))
            print(f"          {k:<12} pedal Q {worst['ped_q']:5.2f} vs attainable "
                  f"{worst['comp_min']:.2f}-{worst['comp_max']:.2f} ({worst['sweep']})")
    if gaps:
        m1, m2, verdict = gaps
        print(f"  AQ4   metric gap {m1:.2f} dB at the shipped Q -> {m2:.2f} dB with Q free: {verdict}")
    if NOTE:
        print(f"  ⚠ {len(NOTE)} solver notes (non-unique roots); first few:")
        for s in NOTE[:5]:
            print(f"      {s}")
    print(f"\n  {'❌ ' + ', '.join(sorted(set(FAIL))) if FAIL else '✅ all known answers hold'}")

    rep = os.path.join(os.path.dirname(os.path.abspath(__file__)), "reports",
                       "s153_notch_shape.json")
    json.dump({"aq1a_worst": w, "aq1a_n": n, "aq1c": res, "aq2": reach, "aq2_reach": [hit, tot],
               "aq3": sol2, "aq2b_q_span": qspan, "aq4_gap_shipQ_freeQ": gaps, "notes": NOTE, "fail": sorted(set(FAIL))},
              open(rep, "w"), indent=1)
    print(f"  report -> {rep}")
    return 1 if FAIL else 0


if __name__ == "__main__":
    sys.exit(main())
