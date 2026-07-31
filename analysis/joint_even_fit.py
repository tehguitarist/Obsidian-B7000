#!/usr/bin/env python3.11
"""joint_even_fit -- the JOINT `clipK` x `jfetSatNeg` screen, on the COMPLETE anchored basis.

WHY THIS EXISTS (session 76 §6, next-step (a))
----------------------------------------------
Two levers on the even-order / series-decay item have been screened SEPARATELY and each was
rejected alone:

    `jfetSatNeg` (the J201's small-signal even coefficient a/2) -- session 73. SELECTIVE for low
        drive (d(low)/d(mid) = 5.4x) but SMALL: its best interior point a=4.0 scores 19.9 on the
        four-statistic sum vs shipped 27.8, and it cannot reach hardware's low-drive H2-H3 at all
        (needs 5.72x selectivity, best available 5.43x). Session 76 added that it barely touches
        the late-harmonic level (<=4 dB against an 11.8 dB deficit).

    `clipK` (the clipper VTC knee hardness) -- session 76. LARGE on both low-drive H2-H3 (it
        delivers d(low) ~ +12.2 dB, the movement session 73 proved the J201 could not make) and on
        the late level (monotone through a genuine SIGN CHANGE, crossing the HW target at k ~ 7-8),
        but NOT selective: it pays for that at low-drive H4-H5 and at both mid pairs, scoring 25.90
        -- better than shipped, clearly worse than the J201's 19.9.

** The two failure modes are complementary and no session has run them together. ** That is the
whole hypothesis here: `clipK` supplies the size that `jfetSatNeg` cannot, `jfetSatNeg` supplies
the low-drive selectivity that `clipK` cannot, and if the effects are even roughly separable on the
statistics then an interior joint point should beat both axes. This screen is a FULL FACTORIAL so
that question is answered by the data rather than by a search: both single-lever axes and the
shipped point are rows of the same grid, measured in the same run at the same guard, so the
comparison never rests on a cross-session number (memory: `rebaseline-all-derived-artefacts`).

THE BASIS IS SIX, NOT FIVE -- and that is a correction to my own next-step
------------------------------------------------------------------------
Session 76 §8(a) says to gate on "all FIVE statistics now available (the four pair statistics plus
the late level)". Checked rather than inherited: its OWN completeness result (§2, GATE 6) is that
the anchor forces `e[H3] = 0`, leaving the anchored error vector with exactly THREE degrees of
freedom `(e2, e4, e5)` PER ANCHOR. There are two anchors. So the complete basis is

        (low  e2, low  e4-e5, low  (e4+e5)/2)      3 dof at the low anchor
        (mid  e2, mid  e4-e5, mid  (e4+e5)/2)      3 dof at the mid anchor    = SIX statistics

"Five" counted the late level once for two anchors. The distinction is not pedantic: the low-drive
and mid-drive late levels are the statistic that carries session 76's own headline, and they move in
OPPOSITE directions (shipped +5.7 dB hot at low drive, -11.8 dB short at mid), so pooling them would
cancel the finding. This file scores all six and reports which subset each verdict rests on.

WHAT EACH SCORE IS FOR
    S_free  sum |error vs HW| over the statistics the TWO INDEPENDENT reference columns AGREE on
            (low H4-H5, 1 dB apart; low LATE, 5 dB apart). ** THE RANKING STATISTIC **, because it
            is the half of the evidence that no chart-authority argument can move: our error there
            is the same against HW and against ND. Derived from HL.REF, not chosen -- see FREE_KEYS.
    S_hw    the four SPLIT statistics (low/mid H2-H3, mid H4-H5, mid LATE), where HW and ND are
            14-28 dB apart so only HW's unverified chart column speaks. Reported BESIDE S_free and
            never summed with it: a candidate that wins here and loses there has not been shown to
            be better, it has been shown to depend on the reference question.
    S6      S_free + S_hw = the complete basis. Printed because it is complete, but it silently
            averages the two authorities, which is exactly the mistake §1 exists to prevent.
    S4      session 73's four-statistic sum, kept ONLY so this run is comparable to the record
            (ship 27.80 | a=2.0 23.3 | a=4.0 19.9 | a=5.6 20.0 | clipK=4 29.55 | clipK=8 25.90).
            The tool CHECKS the shipped row against the record and fails loudly if it does not
            reproduce -- the baseline-first rule built in rather than left to the operator.

THE GUARD IS 2.5 s AND THAT IS LOAD-BEARING
-------------------------------------------
`clipK` sharpens the clipper knee, and session 76 found GATE 4 (duplicate cells, ascending vs
descending neighbours) failing progressively as it rises -- 0.053 dB at shipped, 1.02 at k=4,
9.40 at k=8 -- on exactly the cells GATE 4 was built for. It discriminated the cause rather than
guessing: raising the guard 1.0 -> 2.5 s collapsed the contamination to 0.0803 dB / 0 cells, so it
is the output coupling network's ~220 ms envelope transient, not the clipper's warm-started Newton
solve going history-dependent. ** So the guard's ADEQUACY IS CANDIDATE-DEPENDENT: it is sized
against a LINEAR settling time, and a harder nonlinearity responds to that same residual transient
more strongly. ** Every candidate here sharpens the knee, so the whole grid runs at 2.5 s and GATE 4
is re-checked per candidate rather than inherited -- a contaminated candidate is REFUSED, not
reported with a caveat.

The stimulus is written to a GUARD-STAMPED path. `bounds` and the WAV must agree, and until this
session `measure_all` always read one shared `stimulus.wav`, so a sweep needing a longer guard left
a 2.5 s file where the next default run would index it with 1.0 s bounds -- every analysis window
landing in the wrong place. Session 76 hit that and wrote a warning into the handover; a warning is
not a mechanism.

Run:
  /opt/homebrew/bin/python3.11 analysis/joint_even_fit.py --selftest
  /opt/homebrew/bin/python3.11 -u analysis/joint_even_fit.py --quick --jobs 6
  /opt/homebrew/bin/python3.11 -u analysis/joint_even_fit.py --jobs 6
"""
import sys, os, json, argparse, io, contextlib
from concurrent.futures import ProcessPoolExecutor

sys.path.insert(0, os.path.dirname(__file__))
import numpy as np

# ONE oracle for the measurement: stimulus, anchor logic, pair/level statistics and GATE 4 all come
# from the tool that produced the session-72/76 record. A fast private copy of a shared solve is a
# silent-divergence trap (session 62).
import harmonic_ladder as HL
with contextlib.redirect_stdout(io.StringIO()):
    from fit_nonlinear import min_slope

# Shipped values (FitParams.h, session-44 A5 re-fit). Here ONLY so a candidate's implied
# monotonicity can be scanned and so the grid's own axes are labelled; the RENDER always takes the
# shipped defaults unless a candidate overrides them, so these cannot become the source of truth
# for the audio.
SHIP = dict(clipK=2.4653, jfetSatPos=0.4559, jfetSatNeg=0.76054,
            jfetCeilPos=2.0111, jfetCeilNeg=0.65743, jfetExpandBeta=0.46279)

GUARD_SEC = 2.5           # see the module docstring -- candidate-dependent, not cosmetic

# --- the grid -----------------------------------------------------------------------------------
# Full factorial. Both axes START at the shipped value, so row 0 / column 0 ARE the single-lever
# screens and the (0,0) cell IS the shipped baseline -- every comparison this file makes is
# within-run. `jfetSatNeg` stops at 5.6 because a*s = 2.55 is already at the fold-back edge
# (2.598) at the shipped knee; `clipK` stops at 8.0 because session 76 measured the late-level sign
# change at k ~ 7-8, so the interesting region is bracketed rather than extrapolated into.
CLIPK = (2.4653, 4.0, 6.0, 8.0)
SATNEG = (0.76054, 2.0, 4.0, 5.6)

# --- the statistics -----------------------------------------------------------------------------
STATS = [("low", "H2-H3"), ("low", "H4-H5"), ("low", "LATE"),
         ("mid", "H2-H3"), ("mid", "H4-H5"), ("mid", "LATE")]
S4_KEYS = [("low", "H2-H3"), ("low", "H4-H5"), ("mid", "H2-H3"), ("mid", "H4-H5")]

# The record, so the baseline-first check is IN the tool. Session 73 §3 (pairs, and the 27.80 sum)
# and session 76 §3 (the late levels, as value = HW target + the recorded error vs HW).
SHIP_RECORD = {("low", "H2-H3"): +1.35, ("low", "H4-H5"): +7.45, ("low", "LATE"): -21.30,
               ("mid", "H2-H3"): -1.60, ("mid", "H4-H5"): +1.50, ("mid", "LATE"): -23.85}
RECORD_TOL = 0.5          # dB; far below any finding here, and the run is deterministic


def col_targets(col):
    """One reference column's own value of each statistic, built from HL.REF so there is exactly
    one reference table in the project (never transcribed -- memory:
    `rebuild-targets-dont-transcribe`)."""
    t = {}
    for lbl in ("low", "mid"):
        H = HL.REF[lbl][col]
        t[(lbl, "H2-H3")] = H[2] - H[3]
        t[(lbl, "H4-H5")] = H[4] - H[5]
        t[(lbl, "LATE")] = (H[4] + H[5]) / 2.0 - H[3]
    return t


TARGET = col_targets("HW")
TARGET_ND = col_targets("ND")

# ---- THE AUTHORITY PARTITION, DERIVED -----------------------------------------------------------
# ** This replaces a hand-reasoned "robust subset" that was exactly BACKWARDS, and the error is
# worth keeping because it would have manufactured a false positive. **
#
# Session 76 §7 notes HW's low-drive H4/H5 are chart reads at -60.5/-75.5 dB re fundamental, at the
# bottom of a PNG -- the least reliable numbers in the reference set. I turned that into a "robust"
# subset that DROPPED the two low-drive late statistics, and on that subset the joint fit looked
# like a 3.2x improvement. It is the wrong test. `reference-sources.md` §1 does not rank authority
# by how legible a number was; it ranks it by WHICH COLUMN SPEAKS -- and the operative question,
# already encoded in `HL.MIN_SPAN_DB` and answerable from `HL.REF` alone, is whether the two
# INDEPENDENT reference columns AGREE on a statistic:
#
#   low H4-H5   HW +15.0  ND +14.0   ->  1 dB apart  =>  AGREE, authority-free
#   low LATE    HW -27.0  ND -22.0   ->  5 dB apart  =>  AGREE, authority-free
#   low H2-H3   HW +18.5  ND  +0.0   -> 18 dB apart  =>  SPLIT, HW alone speaks
#   mid H2-H3   HW  +0.0  ND -27.0   -> 27 dB apart  =>  SPLIT
#   mid H4-H5   HW  +0.0  ND -28.0   -> 28 dB apart  =>  SPLIT
#   mid LATE    HW -12.0  ND -26.0   -> 14 dB apart  =>  SPLIT
#
# So the two statistics I dropped as "unreliable" are the only two that a SECOND, independent
# reference corroborates -- and they are exactly where the `clipK` candidates pay their cost. A
# subset chosen by my prose about which numbers looked shaky, rather than by the reference set's own
# agreement, silently became a subset chosen to exclude the candidate's costs (memory:
# `self-selecting-scores`, `defective-rows-must-not-vote`). ** And the tell was free: the tool
# already held MIN_SPAN_DB and both columns; I reasoned instead of asking it. **
FREE_KEYS = [k for k in STATS if abs(TARGET[k] - TARGET_ND[k]) < HL.MIN_SPAN_DB]
SPLIT_KEYS = [k for k in STATS if k not in FREE_KEYS]


def feasible(over):
    """Monotonicity of the implied J201 map. SCANNED, not derived from a closed form: with a finite
    ceiling the fold-back constraint couples s, a and the ceilings, and this replica is the one
    JfetStageTest gates against the shipped C++ map (memory: `verify-extremum-derived-bounds`).
    `clipK` does not enter -- it is the CLIPPER's knee, a different stage."""
    p = dict(SHIP, **over)
    ms = min_slope(p["jfetSatPos"], p["jfetSatNeg"], p["jfetCeilPos"], p["jfetCeilNeg"],
                   p["jfetExpandBeta"])
    return ms, ms > -1.0e-9, p["jfetSatNeg"] * p["jfetSatPos"]


def stats_of(rows, lrows):
    """The six pooled statistics, or None if ANY of them is missing.

    ** All-or-nothing on purpose. ** A candidate that reaches three of the four (tone, anchor) pairs
    would otherwise be scored over a different member set than its neighbours, and an aggregate
    compared across differing membership is this project's most-repeated defect
    (memory: `aggregate-moved-check-membership-first`, seven prior appearances)."""
    s, per_tone = {}, {}
    for lbl in ("low", "mid"):
        for a, b in ((2, 3), (4, 5)):
            v = {r["tone"]: r["corr"] for r in rows if r["drive"] == lbl and r["pair"] == (a, b)}
            if len(v) != len(HL.TONES_HZ):
                return None, None
            s[(lbl, f"H{a}-H{b}")] = float(np.mean(list(v.values())))
            per_tone[(lbl, f"H{a}-H{b}")] = v
        v = {r["tone"]: r["corr"] for r in lrows if r["drive"] == lbl}
        if len(v) != len(HL.TONES_HZ):
            return None, None
        s[(lbl, "LATE")] = float(np.mean(list(v.values())))
        per_tone[(lbl, "LATE")] = v
    return s, per_tone


def score(s, keys):
    return float(sum(abs(s[k] - TARGET[k]) for k in keys))


def run_one(job):
    """Render + measure one grid cell. Must not print -- 6 interleaved workers are unreadable, so
    everything learned comes back in the dict."""
    idx, name, over, bounds, stim, keep = job
    fit = tuple(f"{k}={v!r}" for k, v in over.items())
    stem = f"_jnt{idx}"
    with contextlib.redirect_stdout(io.StringIO()):
        # ** The stimulus is built ONCE by the parent and only READ here. ** Letting each worker
        # call build_stimulus() on a shared path had 8 processes writing one WAV concurrently: the
        # content is deterministic, so it looks fine most of the time and tears occasionally, which
        # is the worst possible failure mode for an A/B (session 73 item 5a).
        cells, fr = HL.measure_all(bounds, 8, fit, stem, stim)
        repeat_ok = bool(HL.gate_repeat(cells))
        verdicts, hits, gates = HL.measure_verdict(cells)
        rows = HL.pair_rows(verdicts, fr)
        lrows = HL.level_rows(verdicts, fr)
    worst_rep = float(max(c["repeat"] for c in cells.values()))
    n_bad = int(sum(1 for c in cells.values() if c["repeat"] > 0.5))
    s, per_tone = stats_of(rows, lrows)
    # The authority-free tracker: RAW per-order H5 at mid drive, where HL.REF has HW and ND
    # AGREEING at -24 dB, so our error there needs no authority argument at all (session 76 §3).
    # ** Different convention from the six statistics above (raw absolute Hn/H1, no filter
    # correction) -- carried alongside them, never summed into them. **
    h5 = {f0: (verdicts[(f0, "mid")][5][0] - HL.REF["mid"]["HW"][5],
               verdicts[(f0, "mid")][5][1])
          for f0 in HL.TONES_HZ if verdicts.get((f0, "mid"))}
    # The FULL per-order raw picture, so the authority partition can be read per ORDER as well as
    # per statistic without re-rendering. At LOW drive HW and ND agree on H3/H4/H5 (0/3.5/4.5 dB
    # apart) and split only on H2; at MID drive they agree on H3 and H5 only. So the per-order view
    # is where the authority-free evidence is densest, and it costs nothing to carry.
    perorder = {f"{f0:g}|{lbl}|H{n}": [verdicts[(f0, lbl)][n][0] - HL.REF[lbl]["HW"][n],
                                       verdicts[(f0, lbl)][n][0] - HL.REF[lbl]["ND"][n],
                                       verdicts[(f0, lbl)][n][1]]
                for f0 in HL.TONES_HZ for lbl in ("low", "mid") for n in (2, 3, 4, 5)
                if verdicts.get((f0, lbl))}
    reach = {(f0, lbl): len(hits[(f0, lbl)]) for f0 in HL.TONES_HZ for lbl in ("low", "mid")}
    if not keep:
        for d in HL.DRIVES:
            try:
                os.remove(f"{HL.WORK}/render{stem}_drv{d:.2f}.wav")
            except OSError:
                pass
    return dict(idx=idx, name=name, over=over, fit=list(fit), stats=s, per_tone=per_tone,
                repeat_ok=repeat_ok, worst_rep=worst_rep, n_bad=n_bad,
                reach={f"{k[0]:g}|{k[1]}": v for k, v in reach.items()},
                h5={f"{f0:g}": h5[f0] for f0 in h5}, perorder=perorder,
                anchor_spread={f"{f0:g}": gates[f0][1] for f0 in HL.TONES_HZ})


def selftest():
    """Everything checkable without a render."""
    ok = True
    print("=" * 96)
    print("SELFTEST 1 -- the six-statistic basis is COMPLETE and each statistic ROUTES to one mode")
    print("=" * 96)
    print("  Delegated to HL.gate_dof(): a pure late-LEVEL error must read EXACTLY 0.00 on both")
    print("  pair statistics, which is why the third dof had to be added to the score at all.")
    if not HL.gate_dof():
        ok = False
        print("  ** GATE 6 FAILED **")

    print("=" * 96)
    print("SELFTEST 2 -- the AUTHORITY PARTITION, derived from HL.REF (not from prose about which")
    print("              chart reads looked shaky -- see the module comment on FREE_KEYS)")
    print("=" * 96)
    print(f"  A statistic is AUTHORITY-FREE when the two independent reference columns agree on it")
    print(f"  to better than MIN_SPAN_DB = {HL.MIN_SPAN_DB:g} dB, i.e. our error there is the same")
    print(f"  against BOTH and needs no §1 authority argument.")
    print(f"  {'statistic':<14} {'HW':>8} {'ND':>8} {'|HW-ND|':>9}   {'authority':<24} in S4?")
    for k in STATS:
        gap = abs(TARGET[k] - TARGET_ND[k])
        auth = "AGREE -> authority-free" if k in FREE_KEYS else f"SPLIT {gap:.0f} dB -> HW alone"
        print(f"  {k[0] + ' ' + k[1]:<14} {TARGET[k]:+8.1f} {TARGET_ND[k]:+8.1f} {gap:9.1f}   "
              f"{auth:<24} {'yes' if k in S4_KEYS else '-'}")
    if not FREE_KEYS or not SPLIT_KEYS:
        ok = False
        print("  ** FAIL -- the partition is degenerate; S_free/S_hw would not be a contrast **")
    else:
        print(f"  OK -- {len(FREE_KEYS)} authority-free / {len(SPLIT_KEYS)} HW-only. ** The verdict")
        print("     ranks on S_free, because that is the half no chart-authority argument can move.")
        print("     S_hw is reported beside it and the two are NOT summed. **")
    print()

    print("=" * 96)
    print("SELFTEST 3 -- feasibility scan is LIVE and REFUSES a known fold-back")
    print("=" * 96)
    ms_bad, good_bad, _ = feasible(dict(jfetSatNeg=8.0))
    if good_bad:
        ok = False
    print(f"  known fold-back a=8.0 (a*s 3.65): min slope {ms_bad:+.4f}  "
          f"{'** FAIL -- accepted an unphysical shape **' if good_bad else 'OK (refused)'}")
    ms_ship, good_ship, _ = feasible({})
    if not good_ship:
        ok = False
    print(f"  shipped point                   : min slope {ms_ship:+.3e}  "
          f"{'OK (accepted)' if good_ship else '** FAIL **'}")
    print("  grid axis feasibility (clipK does not enter -- it is the clipper's knee):")
    for a in SATNEG:
        ms, good, asx = feasible(dict(jfetSatNeg=a))
        print(f"    jfetSatNeg {a:7.4f}  a*s {asx:5.2f}  min slope {ms:+.4e}  "
              f"{'OK' if good else '** FOLDS BACK -- will be refused **'}")
    print()
    print("=" * 96)
    print(f"SELFTEST 4 -- grid: {len(CLIPK)} clipK x {len(SATNEG)} jfetSatNeg = "
          f"{len(CLIPK) * len(SATNEG)} cells, guard {GUARD_SEC} s")
    print("=" * 96)
    print(f"  clipK      : {', '.join(f'{v:g}' for v in CLIPK)}   (shipped = {SHIP['clipK']:g})")
    print(f"  jfetSatNeg : {', '.join(f'{v:g}' for v in SATNEG)}   "
          f"(shipped = {SHIP['jfetSatNeg']:g})")
    if CLIPK[0] != SHIP["clipK"] or SATNEG[0] != SHIP["jfetSatNeg"]:
        ok = False
        print("  ** FAIL -- axis 0 must be the shipped value, or the grid contains no baseline and")
        print("     every d(...) below would be measured against the wrong origin **")
    else:
        print("  OK -- cell (0,0) is the shipped baseline, so both single-lever axes and the")
        print("     baseline are measured in THIS run at THIS guard; no cross-session comparison.")
    print()
    return ok


def cell_name(i, j):
    k, a = CLIPK[i], SATNEG[j]
    if i == 0 and j == 0:
        return "ship"
    if j == 0:
        return f"k={k:g}"
    if i == 0:
        return f"a={a:g}"
    return f"k={k:g},a={a:g}"


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--jobs", type=int, default=6)
    ap.add_argument("--quick", action="store_true",
                    help="2x2 corner grid (ship, each lever alone, and the joint corner) -- "
                         "validates the whole path end to end in ~1/4 of the time")
    ap.add_argument("--guard", type=float, default=GUARD_SEC)
    ap.add_argument("--keep-renders", action="store_true",
                    help="keep the per-candidate WAVs (~27 MB x 7 x cells). Default deletes them "
                         "after measuring; the JSON keeps every number.")
    ap.add_argument("--json", default="analysis/reports/s77_joint_even_fit.json")
    args = ap.parse_args()

    global CLIPK, SATNEG
    if args.quick:
        CLIPK, SATNEG = (CLIPK[0], CLIPK[-1]), (SATNEG[0], SATNEG[-1])

    if not selftest():
        print("** SELFTEST FAILED -- not screening. **")
        return 1
    if args.selftest:
        print("SELFTEST PASS.")
        return 0

    # Guard-stamped path: `bounds` and the file must agree, and a shared name is how a 2.5 s
    # stimulus ends up being indexed with 1.0 s bounds.
    stim = f"{HL.WORK}/stimulus_g{args.guard:.2f}.wav"
    with contextlib.redirect_stdout(io.StringIO()):
        bounds = HL.build_stimulus(stim, args.guard)
    print(f"stimulus: {len(bounds)} segments, guard {args.guard} s -> {stim}")

    jobs, idx = [], 0
    for i in range(len(CLIPK)):
        for j in range(len(SATNEG)):
            over = {}
            if i:
                over["clipK"] = CLIPK[i]
            if j:
                over["jfetSatNeg"] = SATNEG[j]
            jobs.append((idx, cell_name(i, j), over, bounds, stim, args.keep_renders))
            idx += 1
    print(f"screening {len(jobs)} cells x {len(HL.DRIVES)} drives at OS 8, {args.jobs} workers ...")
    print(f"CONDITION: guard {args.guard} s, LEVEL max / BLEND max (bleed-free), EQ/ATTACK/GRUNT flat\n")
    with ProcessPoolExecutor(max_workers=args.jobs) as ex:
        res = list(ex.map(run_one, jobs))
    by = {r["name"]: r for r in res}

    # ---- ADMISSIBILITY, before any number is ranked ------------------------------------------
    print("=" * 96)
    print("GATE -- admissibility per cell (a REFUSED cell is not scored, not caveated)")
    print("=" * 96)
    print(f"  {'cell':<14} {'feas':>5} {'a*s':>5}  {'GATE4 worst':>12} {'bad':>4}  "
          f"{'anchors':>8}  verdict")
    adm = {}
    for r in res:
        ms, good, asx = feasible(r["over"])
        reach_ok = r["stats"] is not None
        okc = good and r["repeat_ok"] and reach_ok
        adm[r["name"]] = okc
        why = []
        if not good:
            why.append("FOLDS BACK")
        if not r["repeat_ok"]:
            why.append(f"GATE 4 ({r['n_bad']} cells)")
        if not reach_ok:
            why.append(f"ANCHOR NOT REACHED {r['reach']}")
        print(f"  {r['name']:<14} {'ok' if good else 'FOLD':>5} {asx:5.2f}  "
              f"{r['worst_rep']:12.4f} {r['n_bad']:4d}  "
              f"{sum(1 for v in r['reach'].values() if v):>3}/4    "
              f"{'ADMITTED' if okc else '** REFUSED: ' + ', '.join(why) + ' **'}")
    print(f"\n  GATE 4 is re-checked PER CELL at guard {args.guard} s rather than inherited: every")
    print("  candidate here sharpens the clipper knee, and the guard is sized against a LINEAR")
    print("  settling time, so its adequacy is candidate-dependent (session 76 §5).")

    # ---- BASELINE-FIRST: the shipped cell must reproduce the record --------------------------
    print()
    print("=" * 96)
    print("BASELINE CHECK -- the shipped cell vs the session-73/76 record")
    print("=" * 96)
    sh = by["ship"]["stats"]
    base_ok = sh is not None
    if sh is None:
        print("  ** the shipped cell did not produce a complete statistic set -- nothing is "
              "comparable **")
    else:
        print(f"  {'statistic':<14} {'measured':>9} {'record':>9} {'delta':>8}   {'HW':>7} {'|err|':>7}")
        for k in STATS:
            d = sh[k] - SHIP_RECORD[k]
            if abs(d) > RECORD_TOL:
                base_ok = False
            print(f"  {k[0] + ' ' + k[1]:<14} {sh[k]:+9.2f} {SHIP_RECORD[k]:+9.2f} {d:+8.2f}"
                  f"{'  **' if abs(d) > RECORD_TOL else '    '}"
                  f"{TARGET[k]:+7.1f} {abs(sh[k] - TARGET[k]):7.2f}")
        s4 = score(sh, S4_KEYS)
        print(f"\n  S4 (session 73's metric) = {s4:.2f}   record 27.80   "
              f"delta {s4 - 27.80:+.2f}  "
              f"{'OK' if abs(s4 - 27.80) <= RECORD_TOL else '** DOES NOT REPRODUCE **'}")
        if abs(s4 - 27.80) > RECORD_TOL:
            base_ok = False
        print(f"  S6 (complete basis)      = {score(sh, STATS):.2f}")
        print(f"  S_free (authority-free)  = {score(sh, FREE_KEYS):.2f}   "
              f"S_hw (HW column alone) = {score(sh, SPLIT_KEYS):.2f}")
    if not base_ok:
        print("\n  ** BASELINE DOES NOT REPRODUCE -- every d(...) below would be measured against")
        print("  the wrong origin. Not ranking. **")
        return 1
    print("\n  OK -- the record reproduces, so the grid's origin is the same point sessions 73")
    print("  and 76 scored, and the longer guard does not bias the comparison.")

    # ---- THE GRID ---------------------------------------------------------------------------
    def cell(i, j):
        r = by[cell_name(i, j)]
        return r if adm[r["name"]] else None

    for label, keys in (("S_free -- AUTHORITY-FREE only (both reference columns agree) "
                         "** THE RANKING STATISTIC **", FREE_KEYS),
                        ("S_hw -- the SPLIT statistics, where only HW's unverified column speaks",
                         SPLIT_KEYS),
                        ("S6 -- COMPLETE basis (S_free + S_hw)", STATS),
                        ("S4 -- session 73's four-statistic metric (for comparability)", S4_KEYS)):
        print()
        print("=" * 96)
        print(f"GRID: {label}.  sum |error vs HW|, dB. LOWER IS BETTER.")
        print("=" * 96)
        print(f"  {'clipK vs a':>12}  " + "".join(f"{a:>10.4g}" for a in SATNEG))
        for i, k in enumerate(CLIPK):
            row = []
            for j in range(len(SATNEG)):
                c = cell(i, j)
                row.append(f"{score(c['stats'], keys):10.2f}" if c else f"{'REFUSED':>10}")
            print(f"  {k:12.4g}  " + "".join(row))
        print("  (row 0 = clipK shipped => that row IS the `jfetSatNeg`-alone screen;")
        print("   column 0 = jfetSatNeg shipped => that column IS the `clipK`-alone screen)")

    # ---- SEPARABILITY: is the joint effect predictable from the two axes? --------------------
    print()
    print("=" * 96)
    print("SEPARABILITY -- is the joint effect the SUM of the two single-lever effects?")
    print("=" * 96)
    print("  For each interior cell, prediction = S(k,a0) + S(k0,a) - S(k0,a0), i.e. what S6 would")
    print("  be if the levers acted independently. The residual is the INTERACTION.")
    print("  ** This is the hypothesis under test, not a diagnostic: `complementary levers` only")
    print("  means anything if their effects do not cancel each other on the same statistics. **")
    print(f"  {'cell':<14} {'S_free act':>11} {'pred':>8} {'inter':>8}   "
          f"{'S6 act':>8} {'pred':>8} {'inter':>8}")
    inter, inter_free = [], []
    for i in range(1, len(CLIPK)):
        for j in range(1, len(SATNEG)):
            c, ck, ca = cell(i, j), cell(i, 0), cell(0, j)
            if not (c and ck and ca):
                continue
            cols = []
            for keys, acc in ((FREE_KEYS, inter_free), (STATS, inter)):
                s00 = score(cell(0, 0)["stats"], keys)
                act = score(c["stats"], keys)
                pred = score(ck["stats"], keys) + score(ca["stats"], keys) - s00
                acc.append(abs(act - pred))
                cols.append(f"{act:11.2f} {pred:8.2f} {act - pred:+8.2f}")
            print(f"  {c['name']:<14} " + "   ".join(cols))
    if inter:
        print(f"\n  S_free: worst |interaction| {max(inter_free):.2f} dB, mean "
              f"{np.mean(inter_free):.2f} dB  (baseline {score(cell(0, 0)['stats'], FREE_KEYS):.2f})")
        print(f"  S6    : worst |interaction| {max(inter):.2f} dB, mean {np.mean(inter):.2f} dB  "
              f"(baseline {score(cell(0, 0)['stats'], STATS):.2f})")
        print("  Small => the levers are separable and the grid's optimum is predictable from its")
        print("  edges. Large => they genuinely interact, and only the joint scan can find it.")

    # ---- PER-STATISTIC DECOMPOSITION of the best cell ---------------------------------------
    print()
    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    adms = [r for r in res if adm[r["name"]]]
    best = min(adms, key=lambda r: score(r["stats"], FREE_KEYS))
    bi = [(i, j) for i in range(len(CLIPK)) for j in range(len(SATNEG))
          if cell_name(i, j) == best["name"]][0]
    axis_only = [r for r in adms if r["name"] != "ship"
                 and (not r["over"].get("clipK") or not r["over"].get("jfetSatNeg"))]
    best_axis = min(axis_only, key=lambda r: score(r["stats"], FREE_KEYS)) if axis_only else None
    interior = bi[0] > 0 and bi[1] > 0
    sfree0 = score(sh, FREE_KEYS)

    print(f"  Best on S_free (the authority-free half): {best['name']}   "
          f"S_free {score(best['stats'], FREE_KEYS):.2f}  (ship {sfree0:.2f})   "
          f"S_hw {score(best['stats'], SPLIT_KEYS):.2f}   S6 {score(best['stats'], STATS):.2f}")
    print(f"  The S_free optimum is "
          f"{'INTERIOR (a genuinely joint point)' if interior else 'ON AN AXIS (a single lever)'}"
          f" at clipK={CLIPK[bi[0]]:g}, jfetSatNeg={SATNEG[bi[1]]:g}.")
    if best["name"] == "ship":
        print("  ** => NO CANDIDATE BEATS THE SHIPPED POINT on the half of the evidence that two")
        print("     independent references corroborate. The joint fit does not pay. **")
    elif interior and best_axis:
        gain = score(best_axis["stats"], FREE_KEYS) - score(best["stats"], FREE_KEYS)
        print(f"  => the joint point beats the best single lever by {gain:.2f} dB on S_free"
              f"{' -- the pairing pays' if gain > 0.5 else ' -- i.e. essentially not at all'}.")
    elif not interior:
        print("  => ** the pairing does NOT pay: no interior cell beats the better single lever. **")

    # ** THE TWO HALVES DISAGREE AND THAT IS THE RESULT, not a caveat to be smoothed over. **
    print()
    tops = {}
    for nm, keys in (("S_free", FREE_KEYS), ("S_hw", SPLIT_KEYS), ("S6", STATS), ("S4", S4_KEYS)):
        tops[nm] = min(adms, key=lambda r: score(r["stats"], keys))["name"]
    print("  WHICH CELL WINS, BY WEIGHTING:  " +
          "   ".join(f"{nm} -> {v}" for nm, v in tops.items()))
    if len(set(tops.values())) == 1:
        print("  => the same cell wins under every weighting, so the verdict does not depend on the")
        print("     authority question at all.")
    else:
        print("  => ** THE WEIGHTINGS DISAGREE, AND THE SPLIT IS EXACTLY THE AUTHORITY SPLIT. ** So")
        print("     the ranking is not a modelling result -- it is a question about the REFERENCE")
        print("     DATA. Any candidate quoted from the S_hw column rests entirely on HW's chart")
        print("     column being right where ND contradicts it, which is precisely what")
        print("     reference-sources.md §5 says not to lean on ('the POSITION is the finding, the")
        print("     exact dB is not'). Resolve the reference before ranking on S_hw.")

    print()
    print("  PER-STATISTIC, the S_hw winner vs shipped -- so the trade is visible per mode.")
    hwin = by[tops["S_hw"]]
    print(f"  {'statistic':<14} {'auth':>6} {'HW':>7} {'ND':>7}  {'ship':>8} {'err':>7}   "
          f"{'cand':>8} {'err':>7}   {'moved':>7}")
    for k in STATS:
        e0, e1 = sh[k] - TARGET[k], hwin["stats"][k] - TARGET[k]
        flag = "better" if abs(e1) < abs(e0) - 0.05 else ("WORSE" if abs(e1) > abs(e0) + 0.05 else "~same")
        print(f"  {k[0] + ' ' + k[1]:<14} {'FREE' if k in FREE_KEYS else 'hw':>6} "
              f"{TARGET[k]:+7.1f} {TARGET_ND[k]:+7.1f}  {sh[k]:+8.2f} {e0:+7.2f}   "
              f"{hwin['stats'][k]:+8.2f} {e1:+7.2f}   {hwin['stats'][k] - sh[k]:+7.2f}  {flag}")
    print(f"  (candidate = {hwin['name']}, the cell that wins on the HW-only half)")

    print()
    print("  AUTHORITY-FREE PER-ORDER TRACKER -- raw Hn/H1 error at the orders where HL.REF's two")
    print("  columns AGREE, so no §1 authority argument is needed. ** Different convention from the")
    print("  six statistics above (absolute, no filter correction) -- carried beside them, never")
    print("  summed in. ** low H4/H5 agree to 3.5/4.5 dB; mid H5 agrees exactly; H3 is the anchor.")
    freeord = [(lbl, n) for lbl in ("low", "mid") for n in (2, 3, 4, 5)
               if abs(HL.REF[lbl]["HW"][n] - HL.REF[lbl]["ND"][n]) < HL.MIN_SPAN_DB and n != 3]
    print(f"  {'cell':<12}  " + "  ".join(f"{lbl[0] + 'H' + str(n) + ' 997/800':>16}"
                                          for lbl, n in freeord))
    for r in sorted(adms, key=lambda r: score(r["stats"], FREE_KEYS)):
        cs = []
        for lbl, n in freeord:
            vs = [r["perorder"].get(f"{f0:g}|{lbl}|H{n}", [float('nan')])[0] for f0 in HL.TONES_HZ]
            cs.append(f"{vs[0]:+7.1f}/{vs[1]:+7.1f}")
        print(f"  {r['name']:<12}  " + "  ".join(cs))
    print("  (mid H5 is session 76's headline: shipped sits 14.5-16.9 dB below BOTH references, the")
    print("   largest authority-free nonlinear error currently measured in this project.)")

    print()
    print("  ** NOT A SHIP PROPOSAL. ** Per reference-sources.md §1(0) any even-order/series move")
    print("  MUST regress on the 129-capture matrix (the captures ARE the ND column), and that")
    print("  regression has to be measured and reported, not discovered later. `clipK` is also the")
    print("  session-44 A5 fit's own parameter, evaluated there inside a harmonic-RATIO objective,")
    print("  so moving it invalidates that fit and would require re-running it.")

    out = dict(guard=args.guard, clipK=list(CLIPK), satneg=list(SATNEG),
               targets={f"{k[0]}|{k[1]}": TARGET[k] for k in STATS},
               targets_nd={f"{k[0]}|{k[1]}": TARGET_ND[k] for k in STATS},
               authority={f"{k[0]}|{k[1]}": ("FREE" if k in FREE_KEYS else "hw") for k in STATS},
               ship_record={f"{k[0]}|{k[1]}": SHIP_RECORD[k] for k in STATS},
               admissible={k: bool(v) for k, v in adm.items()},
               interaction=dict(worst=float(max(inter)) if inter else None,
                                mean=float(np.mean(inter)) if inter else None,
                                worst_free=float(max(inter_free)) if inter_free else None,
                                mean_free=float(np.mean(inter_free)) if inter_free else None),
               best=best["name"], best_interior=bool(interior),
               best_axis=(best_axis["name"] if best_axis else None),
               tops=tops,
               results=[dict(name=r["name"], over=r["over"], fit=r["fit"],
                             repeat_ok=r["repeat_ok"], worst_rep=r["worst_rep"],
                             n_bad=r["n_bad"], reach=r["reach"], h5=r["h5"],
                             perorder=r["perorder"], anchor_spread=r["anchor_spread"],
                             stats=({f"{k[0]}|{k[1]}": r["stats"][k] for k in STATS}
                                    if r["stats"] else None),
                             per_tone=({f"{k[0]}|{k[1]}|{t:g}": v
                                        for k in STATS for t, v in r["per_tone"][k].items()}
                                       if r["per_tone"] else None),
                             S6=(score(r["stats"], STATS) if r["stats"] else None),
                             S4=(score(r["stats"], S4_KEYS) if r["stats"] else None),
                             S_free=(score(r["stats"], FREE_KEYS) if r["stats"] else None),
                             S_hw=(score(r["stats"], SPLIT_KEYS) if r["stats"] else None))
                        for r in res])
    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as f:
        json.dump(out, f, indent=1, default=str)
    print(f"\nwrote {args.json}")
    if not args.keep_renders:
        print(f"(per-candidate renders deleted; --keep-renders to retain them. "
              f"{stim} is guard-stamped and kept.)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
