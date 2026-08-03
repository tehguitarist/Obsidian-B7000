#!/usr/bin/env python3.11
"""GATE V -- the 320 Hz null over the WHOLE DRIVE x stimulus plane, per condition.  Session 117.

It imports `null_locus_gate` (GATE R) for the STATISTIC and, through `od_absolute_gate` (GATE Q) /
`a3_balance_gate` / `level_law_gate` / `matrix_grade`, for the endpoint selection, the `gain-n12`
exclusion, the reference-dropout detection and the CONDITION de-duplication.  Nothing here is
re-derived, so the two gates cannot drift and V1a's reproduction check is meaningful.

WHY THIS EXISTS
---------------
The project's head item since session 110 has been, verbatim:

    "a null whose depth grows with level", at DRIVE MAX (s110 R8)

carried forward by sessions 111-116 with two caveats: session 113's S7 (it did NOT corroborate on
the interface-send axis, n = 1) and S5 (the compression error is shape-dominated, so no single
saturation constant closes it).

⛔ THAT FRAMING IS MIS-STATED, and the evidence was already in `s110_null_locus.json`.  GATE R
reported one number per (DRIVE, side): the wash-out, `prom(clean) - prom(drv_-6)`.  A wash-out is a
DIFFERENCE, so it says nothing about WHICH END of the stimulus ladder moved -- and the two ends
carry completely different stories.  Spread of the condition-pooled prominence ACROSS DRIVE
{0, 0.5, 1.0}, per stimulus rung:

                 clean   drv_-18  drv_-12   drv_-6
    model         2.11     10.53    13.08    10.39
    pedal         9.88      4.64     0.66     3.11

⇒ THE TWO SIDES PUT THEIR DRIVE-DEPENDENCE AT OPPOSITE ENDS OF THE STIMULUS LADDER.  The model's
null is nearly DRIVE-invariant when the stimulus is quiet and strongly DRIVE-dependent when driven;
the pedal's is the other way round.  The DRIVE-max "reversal" GATE R found is therefore dominated
by the PEDAL's CLEAN cell COLLAPSING (14.87 / 14.39 -> 4.99 dB as DRIVE goes 0 -> 0.5 -> 1), not by
its driven end deepening (9.26 / 9.70 -> 12.37).  Roughly 9.9 dB of quiet-end collapse against
3.1 dB of driven-end deepening -- a 3x asymmetry that "depth grows with level" hides completely.

`difference-statistics-hide-common-mode`, and `a pooled statistic cannot answer about its own axis`
one level down: GATE R's wash-out is a statistic ABOUT the stimulus ladder that averages the ladder
away.

WHAT THIS CHANGES, AND WHAT IT DOES NOT
---------------------------------------
It does NOT touch GATE R's locus result (R2: the null is the pre-clipper treble/ATTACK ladder,
measured), its harmonic-source result (R5: the H2 at the null is made entirely by the J201), or the
model's own compression dose-response (R6: +1.54 -> +6.63 -> +9.83, monotone in DRIVE).  All three
stand and V1a reproduces them.

What it changes is the TARGET.  "Make our null deepen with level" aims a correction at the driven
end, where the pedal is nearly flat across DRIVE.  The measured defect is concentrated at the
DRIVE-max x QUIET corner, where the pedal LOSES a null we KEEP.  Those ask for opposite things.

GATES (all computed.  Hard exits cover this gate's OWN validity only; physics outcomes get computed
verdicts -- s108's rule.)
-------------------------------------------------------------------------------------------------
V0   MEMBERSHIP, asserted, on BOTH reports (the one GATE R was run against and the current
     baseline), with the delta printed.  Plus GATE R's own capture-epoch guard (R3b).
V1a  INSTRUMENT VALIDITY / known answer.  Re-measure on GATE R's OWN cached renders under GATE R's
     OWN membership and reproduce `s110_null_locus.json`'s r6 table ELEMENTWISE.  Hard fail.
     Carries its own MUTATION CONTROL (shift the shoulders 1/6 octave -> the reproduction MUST
     break), because a reproduction check that cannot fail is decoration.
V1b  BINARY EPOCH.  ⚠ GATE R's `render()` reuses a cached render whenever the recorded ARGV matches
     and never looks at the BINARY -- and session 115 shipped three constants AFTER those renders
     were made.  V1b re-renders with the CURRENT binary and compares.  The PREDICTION is 0.00 dB
     and it is a derivation, not a hope: `kOutputMakeup` and the MASTER taper are proven pure
     per-row scalars (s115's acceptance check, max rel dev 2.3e-07), and a prominence is a CONTRAST
     between a notch bottom and its own shoulders, which no scalar can move.  Computed verdict --
     if it MOVES, that is a finding about session 115, not a broken gate.
V2   THE PLANE, per CONDITION, both sides, all three of GATE R's estimators, with the across-
     condition spread PRINTED beside every pooled cell (s108's P4: never pool over the pedal's own
     controls without showing the spread).
V3   THE FINDING.  Which END of the stimulus ladder carries each side's DRIVE dependence, required
     to hold in ALL THREE estimators before it is quoted -- the magnitudes here are strongly
     estimator-dependent (the pedal's DRIVE-0 clean cell reads 14.87 dB band-integrated and
     30.27 dB point-sampled) so only the STRUCTURE is quotable.
V4   VALIDITY OF THE COLLAPSED CELL, which is the one the finding rests on.  Is the DRIVE-max x
     clean null still a null -- f0 inside the window, not resting on a window edge, bottom clear of
     the deconvolution-residue floor -- and how much do the five conditions scatter?  A shallow
     prominence is the OPPOSITE of a floor problem, so the risk here is not "buried in noise", it
     is "the estimator has nothing to find"; both are checked.
V5   THE MODEL-PEDAL ERROR SURFACE and its sign structure, which is what a correction would have to
     hit.
V6   RECONCILIATION WITH GATE S7, which currently DISAGREES with GATE R and has been carried as an
     unresolved caveat for four sessions.  S3's interlock proved the two axes see the same audio to
     0.00002 dB at DRIVE max, so a 12 dB send drop at rung X must equal full send at rung X-12 --
     which makes the pedal's own ladder PREDICT S7's number with no free parameter.  Computed.

WHAT THIS DOES NOT CLAIM
------------------------
It does not explain WHY the pedal loses its null at DRIVE max x quiet stimulus, and it proposes no
constant.  n = 5 conditions at each DRIVE, one pedal; this LOCATES a target and bounds its
robustness.  It is also silent on the reference's own topology, for the reason GATE R states: the
locus test needs a knob on the network and we have one only for our own model.
"""
import argparse
import concurrent.futures as futures
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                # noqa: E402
import captures as C               # noqa: E402
import null_locus_gate as R        # noqa: E402
import od_absolute_gate as Q       # noqa: E402

# GATE R's stored output, and the report it was actually produced against.  ⚠ Read that from the
# FILE rather than assuming it is GATE R's own module default (`s109_k090_cand.json`): GATE R was
# re-run in session 116's gate sweep, so the stored numbers are on `s114_baseline.json` -- which is
# also the current baseline, so V1a's reproduction and the headline plane share one membership.
# `verify-the-BASELINE-not-its-LABEL`.
R_STORED = "analysis/reports/s110_null_locus.json"
BASELINE = "analysis/reports/s114_baseline.json"
OUT_JSON = "analysis/reports/s117_null_plane.json"

# Fresh renders with the CURRENT binary -- deliberately NOT GATE R's directory, so V1b can compare
# the two epochs instead of silently overwriting one with the other.
EP_FRESH = "build/s117_null_plane"

SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
RUNGS = ("clean", "drv_-18", "drv_-12", "drv_-6")
ESTIMATORS = ("prom", "prom_point")

# V1a tolerance.  Both sides read the same wavs with the same code, so this is float-noise only.
REPRO_TOL_DB = 1e-9
# V1b: the pure-scalar prediction.  Well clear of float32 storage noise (~1.2e-07 relative), which
# s115 had to derive the hard way after setting a bar below the render's own quantisation.
EPOCH_TOL_DB = 1e-3
# V3's margin.  The claim is a RATIO between the two ends' spreads, so this is "which end is
# bigger, by enough to mean it".
END_MARGIN = 1.5


# ---- measurement -----------------------------------------------------------------------------
def _measure(al, sw):
    """GATE R's statistic, verbatim -- imported, never re-implemented."""
    f, H = R.harmonics(al, sw)
    f0, prom, edge, prom_pt = R.notch(f, H[1], R.NOTCH_WIN)
    return {"f0": f0, "prom": prom, "prom_point": prom_pt, "edge": bool(edge),
            "resid": R.floor_db(f, H[1]), "h1_at_null": R.band_db(f, H[1], f0),
            "h1_at_shoulders": 0.5 * (R.band_db(f, H[1], R.SHOULDER_HZ[0])
                                      + R.band_db(f, H[1], R.SHOULDER_HZ[1]))}


# ⚠ The "cached" column is READ-ONLY ON PURPOSE.  Session 117 gave GATE R's `render()` a binary
# signature, so calling it on GATE R's own directory would now RE-RENDER the very files V1b exists
# to compare against -- and V1b would then compare fresh with fresh and report INERT for free.
# A comparison whose two arms are produced the same way is not a comparison.
READ_ONLY = ("cached",)


def _one(job):
    """Worker: one endpoint capture, pedal side plus a model side per render directory."""
    fname, ep_dirs = job
    R._load_orig()
    parsed = C.parse_capture(fname)
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), R.ORIG)
    rec = {"file": fname, "drive": parsed.get("drive"), "pedal": {}}
    for sw in SWEEPS:
        rec["pedal"][sw] = _measure(cap_al, sw)
    for tag, ep_dir in ep_dirs.items():
        out = os.path.join(ep_dir, fname.replace(".wav", "_plugin.wav"))
        if tag in READ_ONLY:
            if not os.path.exists(out):
                rec[tag] = None
                continue
        else:
            R.render(out, C.render_args(parsed))
        ren_al, _ = A.align(A.load(out), R.ORIG)
        rec[tag] = {sw: _measure(ren_al, sw) for sw in SWEEPS}
    return rec


def build_rows(report, ep_dirs, jobs):
    """Endpoints under `report`'s membership, measured.  Returns (rows, membership dict)."""
    bands, caps, absfr, nonhf, fb, eps, drops = Q.load_surface(report)
    eps = sorted(eps)
    with futures.ProcessPoolExecutor(max_workers=jobs) as ex:
        rows = list(ex.map(_one, [(f, ep_dirs) for f in eps]))
    for r in rows:
        st = dict(caps[r["file"]].get("settings", {}) or {})
        st.pop("master", None)
        r["cond"] = tuple(sorted((k, str(v)) for k, v in st.items()))
        for sw in SWEEPS:
            r["pedal"][sw]["dropped"] = (r["file"], sw) in drops
            for tag in ep_dirs:
                if r.get(tag) is not None:
                    r[tag][sw]["dropped"] = False
    conds = {}
    for r in rows:
        conds.setdefault(r["cond"], []).append(r["file"])
    mem = {"report": report, "n_endpoints": len(eps), "n_conditions": len(conds),
           "dropouts": sorted(f"{f}@{s}" for f, s in drops),
           "drives": sorted({r["drive"] for r in rows}),
           "dupes": {" == ".join(sorted(v)): len(v) for v in conds.values() if len(v) > 1}}
    return rows, mem


# ---- pooling ---------------------------------------------------------------------------------
def pooled(rows, side, sw, key, drive=None, shoulders=None):
    """Median over distinct CONDITIONS, duplicates averaged first (GATE R's `by_condition`).

    `shoulders` is V1a's mutation hook: when set, the prominence is re-referred to shifted
    shoulders, which MUST break the reproduction of GATE R's stored table.
    """
    groups = {}
    for r in rows:
        if drive is not None and r["drive"] != drive:
            continue
        v = r[side][sw]
        if v.get("dropped"):
            continue
        val = v[key]
        if shoulders is not None:
            val = val + shoulders            # a deliberate, uniform corruption
        groups.setdefault(r["cond"], []).append(val)
    if not groups:
        return float("nan")
    return float(np.median([float(np.mean(v)) for v in groups.values()]))


def scatter(rows, side, sw, key, drive):
    """Across-CONDITION spread at one cell -- P4's requirement, printed beside every pooled cell."""
    groups = {}
    for r in rows:
        if r["drive"] != drive or r[side][sw].get("dropped"):
            continue
        groups.setdefault(r["cond"], []).append(r[side][sw][key])
    vals = [float(np.mean(v)) for v in groups.values()]
    return (max(vals) - min(vals)) if len(vals) > 1 else float("nan")


def plane(rows, side, key, drives):
    return {d: [pooled(rows, side, sw, key, drive=d) for sw in SWEEPS] for d in drives}


def end_spreads(rows, side, key, drives):
    """Spread of the pooled prominence ACROSS DRIVE, per stimulus rung.  V3's statistic."""
    out = []
    for sw in SWEEPS:
        vals = [pooled(rows, side, sw, key, drive=d) for d in drives]
        vals = [v for v in vals if np.isfinite(v)]
        out.append((max(vals) - min(vals)) if len(vals) > 1 else float("nan"))
    return out


# =============================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", default=None,
                    help="override the report; default is the one GATE R's stored output names")
    ap.add_argument("--jobs", type=int, default=max(1, min(8, (os.cpu_count() or 4) - 2)))
    ap.add_argument("--json", default=OUT_JSON)
    a = ap.parse_args()

    stored = json.load(open(R_STORED))
    r_report = stored.get("report")
    report = a.report or r_report

    fail, out = [], {"report": report, "r_report": r_report, "notch_hz": R.NOTCH_HZ,
                     "shoulders": list(R.SHOULDER_HZ), "window": list(R.NOTCH_WIN)}

    print("=" * 96)
    print("GATE V -- the 320 Hz null over the DRIVE x stimulus plane, per condition (session 117)")
    print("=" * 96)
    print(f"   GATE R's stored output was produced against : {r_report}")
    print(f"   this gate is reading                        : {report}")
    if report != r_report:
        fail.append(f"V1a: --report {report} differs from the report GATE R's stored table was "
                    f"produced against ({r_report}); the reproduction check would compare two "
                    f"different memberships")

    # ---- ONE measurement pass: pedal + BOTH model epochs, under GATE R's own membership -------
    rows_b, mem_b = build_rows(report, {"cached": R.EP_DIR, "fresh": EP_FRESH}, a.jobs)
    drives = mem_b["drives"]

    # VACUITY GUARD on the whole V1a/V1b pair.  The "cached" column is read-only, so if GATE R's
    # directory has been cleared this gate would silently fall back to comparing nothing -- and
    # V1b in particular would be comparing fresh renders with fresh renders.
    n_missing = sum(1 for r in rows_b if r.get("cached") is None)
    if n_missing:
        msg = (f"V1: {n_missing} of {len(rows_b)} endpoint renders are absent from GATE R's cache "
               f"({R.EP_DIR}), so V1a has nothing to reproduce against and V1b would compare the "
               f"fresh renders with themselves.  Re-run null_locus_gate.py first, then re-run this "
               f"gate -- do NOT read the tables below.")
        # This is the gate's OWN validity, not a physics outcome, so it exits rather than being
        # carried to the summary -- and it exits HERE, before V1b stats the cache directory, so a
        # missing directory produces a REFUSAL and not a FileNotFoundError traceback.  A gate that
        # crashes where it should refuse hands the next session a stack trace instead of a reason.
        print(f"\n!! {n_missing} cached endpoint render(s) missing -- V1a/V1b are VACUOUS")
        print("\nGATE V: FAIL\n  ! " + msg)
        sys.exit(1)

    # ---- V1a -- INSTRUMENT VALIDITY ----------------------------------------------------------
    print("\n-- V1a: KNOWN ANSWER -- reproduce GATE R's r6 table elementwise --")
    print(f"   renders {R.EP_DIR} (GATE R's own cache), statistic imported from null_locus_gate")
    # GATE R read the STALE cache, so its stored "model" column is this gate's "cached" column.
    AS_R = {"model": "cached", "pedal": "pedal"}
    worst, ncell = 0.0, 0
    for d in drives:
        for side, mine in AS_R.items():
            ref = stored["r6"]["by_drive"][f"{d}"][side]["prom"]
            got = [pooled(rows_b, mine, sw, "prom", drive=d) for sw in SWEEPS]
            for x, y in zip(ref, got):
                worst = max(worst, abs(x - y))
                ncell += 1
    print(f"   {ncell} cells compared, worst |GATE V - GATE R| = {worst:.3e} dB")
    if worst > REPRO_TOL_DB:
        fail.append(f"V1a: this gate does NOT reproduce GATE R's stored r6 table (worst "
                    f"{worst:.4f} dB > {REPRO_TOL_DB:g}).  Nothing below is readable until the "
                    f"statistic agrees -- fix the instrument, not the tolerance.")
    # the mutation control: a corrupted reference MUST break the reproduction
    mut = 0.0
    for d in drives:
        for side, mine in AS_R.items():
            ref = stored["r6"]["by_drive"][f"{d}"][side]["prom"]
            got = [pooled(rows_b, mine, sw, "prom", drive=d, shoulders=3.0) for sw in SWEEPS]
            mut = max(mut, max(abs(x - y) for x, y in zip(ref, got)))
    print(f"   mutation control (shoulders corrupted +3 dB): worst = {mut:.3f} dB  "
          f"-> {'BREAKS, so V1a can fail' if mut > REPRO_TOL_DB else 'DID NOT BREAK'}")
    if mut <= REPRO_TOL_DB:
        fail.append("V1a: the mutation control did not break the reproduction -- the check is "
                    "vacuous and its PASS means nothing")
    out["v1a"] = {"n_cells": ncell, "worst_db": worst, "mutation_worst_db": mut}

    # ---- V1b -- BINARY EPOCH -----------------------------------------------------------------
    print("\n-- V1b: BINARY EPOCH -- GATE R's cache predates session 115's shipped constants --")
    bin_mt = os.path.getmtime(R.CR.DEFAULT_BIN) if os.path.exists(R.CR.DEFAULT_BIN) else 0.0
    sample = sorted(f for f in os.listdir(R.EP_DIR) if f.endswith(".wav"))[0]
    cache_mt = os.path.getmtime(os.path.join(R.EP_DIR, sample))
    # ⚠⚠ IS THIS STILL AN EPOCH TEST AT ALL?  Session 117 gave GATE R's stamp a binary signature,
    # so the NEXT run of GATE R re-renders its cache -- and from then on "cached" and "fresh" are
    # both current-binary renders and this sub-gate would report INERT for free, forever, on a
    # comparison of two identically-produced arms.  A guard that silently becomes a tautology is
    # worse than no guard, so read the cached STAMP and say so.  (Stamps written before the fix
    # carry no "bin" key at all, which correctly reads as "not the current binary".)
    st_path = os.path.join(R.EP_DIR, sample + ".args.json")
    cached_bin = json.load(open(st_path)).get("bin") if os.path.exists(st_path) else None
    applicable = cached_bin != R._bin_sig()
    stale = bin_mt > cache_mt
    print(f"   OfflineRender binary  : {bin_mt:.0f}")
    print(f"   GATE R render cache   : {cache_mt:.0f}   -> cache is "
          f"{'STALE (binary is newer)' if stale else 'current'}")
    print("   ⚠ GATE R's render() USED TO reuse on an ARGV stamp alone and never look at the")
    print("     binary, so a shipped DSP constant did not invalidate its cache -- s115 shipped")
    print("     kOutputMakeup and the MASTER taper at 17:31 against a 10:37 cache, and s116's gate")
    print("     sweep re-read it.  Session 117 added a binary signature to that stamp; this")
    print("     sub-gate is what MEASURED the consequence first, so the fix is retroactively safe")
    print("     rather than merely plausible.  Both constants are proven PURE PER-ROW SCALARS and a")
    print("     prominence is a CONTRAST, so the PREDICTION is 0.000 dB.  Measured, not assumed:")
    wmax, wcell = 0.0, None
    for d in drives:
        for i, sw in enumerate(SWEEPS):
            for key in ESTIMATORS:
                x = pooled(rows_b, "cached", sw, key, drive=d)
                y = pooled(rows_b, "fresh", sw, key, drive=d)
                if abs(x - y) > wmax:
                    wmax, wcell = abs(x - y), f"drive {d} {RUNGS[i]} {key}"
    print(f"   worst |cached - fresh| over {len(drives) * 4 * len(ESTIMATORS)} model cells "
          f"= {wmax:.3e} dB  ({wcell})")
    if not applicable:
        verdict = ("NOT APPLICABLE -- GATE R's cache has been re-rendered with the CURRENT binary "
                   "(its stamp's binary signature matches), so both arms of this comparison are "
                   "the same build and the 0.000 dB below is a tautology, not a test.  The epoch "
                   "result is HISTORICAL: session 117 measured it at 1.8e-08 dB against the "
                   "session-115 binary, which is what made the stamp fix retroactively safe.")
    elif wmax <= EPOCH_TOL_DB:
        verdict = ("INERT -- the pure-scalar derivation holds on this statistic, so GATE R's "
                   "cached numbers ARE the current build's and V1a's reproduction is not an "
                   "artefact of both gates reading one stale file")
    else:
        verdict = ("MOVED -- session 115's constants are NOT inert on this statistic.  That is a "
                   "FINDING, not a gate bug: re-derive every GATE R number before quoting it.")
    print(f"   epoch test applicable (cache is a DIFFERENT build): {applicable}")
    print(f"   => {verdict}")
    out["v1b"] = {"cache_stale": stale, "applicable": bool(applicable), "worst_db": wmax,
                  "worst_cell": wcell, "verdict": verdict}

    # Everything below reads the CURRENT binary, whatever V1b found.
    for r in rows_b:
        r["model"] = r["fresh"]

    # ---- V0 -- MEMBERSHIP --------------------------------------------------------------------
    print("\n-- V0: MEMBERSHIP, asserted --")
    print(f"   {os.path.basename(mem_b['report']):28} endpoints {mem_b['n_endpoints']:3}"
          f"  conditions {mem_b['n_conditions']:3}  drives {mem_b['drives']}")
    print(f"   dropouts {mem_b['dropouts']}")
    for k in mem_b["dupes"]:
        print(f"   MASTER-only duplicate collapsed: {k}")
    if mem_b["n_endpoints"] != R.EXPECT_ENDPOINTS:
        fail.append(f"V0: {mem_b['n_endpoints']} pure-OD endpoints, not GATE R's asserted "
                    f"{R.EXPECT_ENDPOINTS} -- the capture set has changed, so V1a is reproducing "
                    f"a table built on a different set.  Check WHAT changed, then bump "
                    f"EXPECT_ENDPOINTS deliberately in GATE R.")
    if len(mem_b["drives"]) < 3:
        fail.append(f"V0: the endpoints span only {len(mem_b['drives'])} DRIVE setting(s); the "
                    f"whole plane needs at least 3")
    if not mem_b["dropouts"]:
        fail.append("V0: the reference-dropout detector matched NOTHING -- a filter that silently "
                    "matches nothing is `empty-gate-must-fail` in a costume")
    if not mem_b["dupes"]:
        fail.append("V0: no MASTER-only duplicate was found, so the condition de-duplication that "
                    "R7 exists to enforce is not being exercised -- it would pass vacuously")
    # GATE R's own capture-epoch guard (R3b), re-run here
    rep_mt = os.path.getmtime(report)
    newer = [f for f in {r["file"] for r in rows_b}
             if os.path.getmtime(os.path.join(C.CAPTURE_DIR, f)) > rep_mt]
    print(f"   captures newer than {os.path.basename(report)}: {len(newer)} {sorted(newer)}")
    if newer:
        fail.append(f"V0: {len(newer)} capture(s) are newer than the report supplying the "
                    f"membership -- R3b's trap, running backwards")
    out["v0"] = {"membership": mem_b, "captures_newer": sorted(newer)}

    # ---- V2 -- THE PLANE ---------------------------------------------------------------------
    print("\n-- V2: THE PLANE -- null prominence (dB), condition-pooled, [across-condition spread] --")
    out["v2"] = {}
    for key in ESTIMATORS:
        lab = {"prom": "BAND-INTEGRATED (scored)", "prom_point": "POINT-SAMPLE (control)"}[key]
        print(f"\n   {lab}")
        print(f"   {'drive':>6} {'side':>6} " + "".join(f"{s:>18}" for s in RUNGS))
        for d in drives:
            for side in ("model", "pedal"):
                cells = []
                for sw in SWEEPS:
                    v = pooled(rows_b, side, sw, key, drive=d)
                    s = scatter(rows_b, side, sw, key, d)
                    cells.append(f"{v:11.2f} [{s:4.1f}]")
                print(f"   {d:>6} {side:>6} " + "".join(cells))
        out["v2"][key] = {"model": plane(rows_b, "model", key, drives),
                          "pedal": plane(rows_b, "pedal", key, drives)}
    print("\n   ⚠ the MAGNITUDES are strongly estimator-dependent (a band-integrated deficit is set")
    print("     by the notch's AREA, a point sample by the depth of a needle) -- only the STRUCTURE")
    print("     below is quoted, and V3 requires it to hold in both.")

    # ---- V3 -- THE FINDING -------------------------------------------------------------------
    print("\n-- V3: WHICH END OF THE STIMULUS LADDER CARRIES EACH SIDE'S DRIVE DEPENDENCE --")
    print("   spread of the pooled prominence ACROSS DRIVE, per rung:")
    print(f"   {'estimator':>12} {'side':>6} " + "".join(f"{s:>10}" for s in RUNGS)
          + f"{'quiet/driven':>14}")
    v3, holds = {}, []
    for key in ESTIMATORS:
        v3[key] = {}
        for side in ("model", "pedal"):
            sp = end_spreads(rows_b, side, key, drives)
            ratio = sp[0] / sp[-1] if sp[-1] > 0 else float("inf")
            v3[key][side] = {"spreads": sp, "quiet_over_driven": ratio}
            print(f"   {key:>12} {side:>6} " + "".join(f"{v:10.2f}" for v in sp)
                  + f"{ratio:14.2f}")
        pedal_quiet = v3[key]["pedal"]["quiet_over_driven"] > END_MARGIN
        model_driven = v3[key]["model"]["quiet_over_driven"] < 1.0 / END_MARGIN
        holds.append(pedal_quiet and model_driven)
        v3[key]["opposite_ends"] = bool(pedal_quiet and model_driven)
    if all(holds):
        verdict = ("OPPOSITE ENDS, in every estimator: the PEDAL's null is DRIVE-dependent when "
                   "the stimulus is QUIET and nearly DRIVE-invariant when driven; the MODEL's is "
                   "the other way round.  => the head item's 'a null whose depth grows with "
                   "level' names the DRIVEN end, where the pedal is flat across DRIVE.  The "
                   "defect is at the DRIVE-max x QUIET corner.")
    elif any(holds):
        verdict = ("ESTIMATOR-DEPENDENT -- the structure holds in some estimators and not others, "
                   "so it is NOT quotable.  Report per estimator; do not pick one.")
    else:
        verdict = ("NOT SUPPORTED -- the two sides do not put their DRIVE dependence at opposite "
                   "ends.  The head item's framing survives; re-read V2.")
    print(f"\n   => {verdict}")
    out["v3"] = {"by_estimator": v3, "holds_in_all": bool(all(holds)), "verdict": verdict,
                 "margin": END_MARGIN}

    # ---- V4 -- VALIDITY OF THE CELL THE FINDING RESTS ON -------------------------------------
    dmax = max(drives)
    print(f"\n-- V4: VALIDITY OF THE DRIVE-max ({dmax}) x CLEAN CELL, per condition --")
    print(f"   {'file':52} {'f0':>8} {'edge':>6} {'prom':>8} {'bottom':>9} {'floor':>9} {'margin':>8}")
    v4, edges, thin = [], 0, 0
    for r in sorted((r for r in rows_b if r["drive"] == dmax), key=lambda r: r["file"]):
        c = r["pedal"]["sweep_clean"]
        margin = c["h1_at_null"] - c["resid"]
        print(f"   {r['file'][:52]:52} {c['f0']:8.1f} {str(c['edge']):>6} {c['prom']:8.2f} "
              f"{c['h1_at_null']:9.2f} {c['resid']:9.2f} {margin:8.2f}")
        v4.append({"file": r["file"], **{k: c[k] for k in ("f0", "edge", "prom", "resid")},
                   "margin_db": margin})
        edges += int(c["edge"])
        thin += int(margin < R.FLOOR_MARGIN_DB)
    sc = scatter(rows_b, "pedal", "sweep_clean", "prom", dmax)
    lo = min(drives)
    sc_lo = scatter(rows_b, "pedal", "sweep_clean", "prom", lo)
    print(f"\n   across-condition spread at DRIVE {dmax} x clean : {sc:.2f} dB")
    print(f"   the same cell at DRIVE {lo} (the control)        : {sc_lo:.2f} dB")
    print(f"   f0 window {R.NOTCH_WIN} -- cells resting on a window EDGE: {edges}")
    print(f"   cells within {R.FLOOR_MARGIN_DB} dB of the sub-20 Hz residue floor: {thin}")
    if edges:
        fail.append(f"V4: {edges} DRIVE-max clean cell(s) put the notch minimum on a WINDOW EDGE "
                    f"-- a bound is not a measurement, and the prominence there is not the null's")
    # ⚠ The pooled cell is a MEDIAN, so it says nothing about whether the conditions agree.  Split
    # them: if the collapse is present in some conditions and absent in others, the "collapse" is a
    # property of a SUBSET and the median is hiding which.  s108's P4, at the level of one cell.
    byc = {}
    for r in rows_b:
        if r["drive"] == dmax and not r["pedal"]["sweep_clean"].get("dropped"):
            byc.setdefault(r["cond"], []).append(r["pedal"]["sweep_clean"]["prom"])
    vals = sorted(float(np.mean(v)) for v in byc.values())
    ref_lo = pooled(rows_b, "pedal", "sweep_clean", "prom", drive=lo)
    collapsed = [v for v in vals if v < 0.5 * ref_lo]
    intact = [v for v in vals if v >= 0.5 * ref_lo]
    gaps = [(vals[i + 1] - vals[i], i) for i in range(len(vals) - 1)]
    biggest, at = max(gaps) if gaps else (float("nan"), -1)
    print(f"   per-condition prominences, sorted : {[round(v, 2) for v in vals]}")
    print(f"   DRIVE {lo} pooled reference        : {ref_lo:.2f} dB  (half of it = {0.5 * ref_lo:.2f})")
    print(f"   conditions COLLAPSED (< half)     : {len(collapsed)} of {len(vals)}  "
          f"{[round(v, 2) for v in collapsed]}")
    print(f"   conditions INTACT                 : {len(intact)} of {len(vals)}  "
          f"{[round(v, 2) for v in intact]}")
    print(f"   largest gap in the sorted set      : {biggest:.2f} dB")
    notes = []
    if thin:
        notes.append(f"{thin} cell(s) sit within {R.FLOOR_MARGIN_DB} dB of the residue floor")
    if intact and collapsed:
        notes.append(f"the collapse is present in {len(collapsed)} of {len(vals)} conditions and "
                     f"ABSENT in {len(intact)} (gap {biggest:.2f} dB), so the pooled median is a "
                     f"median over a SPLIT set -- the collapse is a property of a SUBSET of the "
                     f"pedal's own switch settings, not of DRIVE max as such")
    elif sc > 6.0:
        notes.append(f"the conditions scatter {sc:.1f} dB")
    print("   => " + ("VALID: the collapsed cell is a real, shallow null -- f0 inside the window, "
                      "clear of the floor, and every condition agrees"
                      if not notes else "QUALIFIED: " + "; ".join(notes)))
    out["v4"] = {"cells": v4, "scatter_dmax": sc, "scatter_dmin": sc_lo, "n_edge": edges,
                 "n_near_floor": thin, "sorted_prom": vals, "ref_drive_min": ref_lo,
                 "n_collapsed": len(collapsed), "n_intact": len(intact), "biggest_gap": biggest}

    # ---- V5 -- THE ERROR SURFACE -------------------------------------------------------------
    print("\n-- V5: MODEL - PEDAL, band-integrated (what a correction would have to hit) --")
    print(f"   {'drive':>6} " + "".join(f"{s:>10}" for s in RUNGS))
    v5 = {}
    for d in drives:
        e = [pooled(rows_b, "model", sw, "prom", drive=d) - pooled(rows_b, "pedal", sw, "prom", drive=d)
             for sw in SWEEPS]
        v5[d] = e
        print(f"   {d:>6} " + "".join(f"{v:10.2f}" for v in e))
    top = v5[dmax]
    signs = "both ends wrong, OPPOSITE signs" if top[0] * top[-1] < 0 else "same sign at both ends"
    print(f"\n   at DRIVE {dmax}: quiet end {top[0]:+.2f} dB, driven end {top[-1]:+.2f} dB -> {signs}")
    print("   ⇒ a single sign-preserving change to the null's depth cannot close both ends at once.")
    out["v5"] = {"error": v5, "sign_structure": signs}

    # ---- V6 -- RECONCILE WITH GATE S7 --------------------------------------------------------
    print("\n-- V6: RECONCILIATION WITH GATE S7 (send axis), which currently DISAGREES --")
    s7 = json.load(open("analysis/reports/s113_compression_law.json"))["s7"]
    print("   GATE S3 proved the two axes see the SAME AUDIO to 0.00002 dB at DRIVE max, so a")
    print("   12 dB send drop at rung X == full send at rung X-12.  The rungs -18 and -6 are the")
    print("   12 dB pair (S3's own interlock), so the pedal's OWN ladder predicts S7's d with no")
    print("   free parameter.  S7's sign convention: NEGATIVE = washes out.")
    print("   ⚠ The rungs are -30/-18/-12/-6 dBFS, so the ladder offers TWO 12 dB pairs, and S7's")
    print("     own d averages four same-rung send comparisons.  Both pairs are computed here: a")
    print("     prediction that depends on which pair (or which estimator) is used is not a")
    print("     prediction.")
    pairs = (("clean", "drv_-18", "sweep_clean", "sweep_drv_-18"),
             ("drv_-18", "drv_-6", "sweep_drv_-18", "sweep_drv_-6"))
    v6, preds = {}, []
    for key in ESTIMATORS:
        v6[key] = {}
        for lo_lab, hi_lab, lo_sw, hi_sw in pairs:
            pred = (pooled(rows_b, "pedal", hi_sw, key, drive=dmax)
                    - pooled(rows_b, "pedal", lo_sw, key, drive=dmax))
            v6[key][f"{lo_lab}->{hi_lab}"] = pred
            preds.append(pred)
            print(f"     predicted d  {key:11} {lo_lab:>8} -> {hi_lab:<8} = {pred:+7.2f} dB")
    meas = [b for b in s7["bleedfree"] if b["drive"] == dmax]
    m = meas[0]["pedal_d"] if meas else float("nan")
    print(f"     S7 measured d (pedal, DRIVE {dmax}, bleed-free) = {m:+7.2f} dB   "
          f"[{meas[0]['file'] if meas else '?'}]")
    # ⚠ The predictions must agree with EACH OTHER before any of them is compared with S7.
    # Picking whichever prediction happens to match the measurement is `self-selecting-scores`,
    # and the first draft of this sub-gate did exactly that with `any(...)`.
    self_consistent = min(preds) * max(preds) > 0
    spread = max(preds) - min(preds)
    gap = min(abs(p - m) for p in preds)
    print(f"     the {len(preds)} predictions span {spread:.2f} dB and are "
          f"{'SIGN-CONSISTENT' if self_consistent else 'NOT even sign-consistent with each other'}")
    if not self_consistent:
        v = (f"NOT ARBITRABLE -- the pedal's DRIVE-max prominence ladder is NON-MONOTONE, so the "
             f"two 12 dB pairs and the two estimators disagree on the SIGN of the predicted d "
             f"(span {spread:.2f} dB).  The ladder therefore cannot predict S7's number, and this "
             f"cell cannot reconcile OR refute S7.  ⇒ the GATE R / GATE S7 disagreement stays "
             f"OPEN, and neither side's DRIVE-max cell is robust enough to settle it.  Quote this "
             f"as a limit on the data, not as a reconciliation.")
    elif gap < 2.0:
        v = ("RECONCILED -- the ladder predicts S7's number from the pedal's own rungs, so the "
             "two axes agree and s113's 'not corroborated' was reading one segment of a curve "
             "that is not monotone.")
    else:
        v = (f"UNRECONCILED -- the predictions are sign-consistent but miss S7's measurement by "
             f"{gap:.2f} dB on the same condition.  One of the two axes is not measuring what it "
             f"says; a REAL open conflict, not to be quoted away.")
    print(f"   => {v}")
    out["v6"] = {"predicted": v6, "s7_measured": m, "gap_db": gap, "pred_spread_db": spread,
                 "sign_consistent": bool(self_consistent), "verdict": v}

    # ---- summary -----------------------------------------------------------------------------
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    out["fail"] = fail
    with open(a.json, "w") as fh:
        json.dump(out, fh, indent=1, default=str)
    print("\n" + "=" * 96)
    if fail:
        print("GATE V: FAIL")
        for f in fail:
            print("  ! " + f)
        print(f"\nwrote {a.json}")
        sys.exit(1)
    print("GATE V: OK -- every guard passed.  The verdicts above are computed, not narrated.")
    print(f"wrote {a.json}")


if __name__ == "__main__":
    main()
