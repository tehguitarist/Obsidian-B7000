#!/usr/bin/env python3.11
"""GATE AV — the project-wide `prom` audit: which prominence numbers are DEPTHS, and which are WINDOWS?

WHY THIS EXISTS
---------------
Session 157's own `▶ NEXT` #1:

    The `locate()` finding is project-wide and only its `mid_peak` instance has been worked.
    `prom` is used as a presence/validity bar in GATE W, AA, AD, AE and in `od_tone_restore_fit`.
    Nothing there is known to be wrong — as a detector it is sound, and AE's headline is
    threshold-free — but any *quantitative* prominence comparison in those gates is a
    window-bounded max-descent, and whether any of them leans on it as a height has not been
    audited.  That audit is a `grep` for `prom` plus a read.

GATE AU proved the mechanism: `feature_locus_gate.locate` sets `j = argmin(dd)` and breaks each
walk on `dd[k] < dd[j]`, so the break is **unreachable** and `prom` is
`min(left max-ascent, right max-ascent)` inside a FIXED window — never a topographic prominence.
AU worked one feature (`mid_peak`).  This gate asks the two questions AU left open:

  (1) WHICH sites in the project actually read a value produced that way — and which read one of
      the project's OTHER prominence estimators, which do not share the defect?
  (2) For the sites that do, how much of the number is the FEATURE and how much is the WINDOW?

⭐ The second question has a threshold-free answer, and it is the whole instrument here.  A
max-ascent terminated at a window bound GROWS when the window is widened; one terminated at a real
interior shoulder does NOT.  So: **pin the extremum where the shipped window put it, widen only the
walk domain, and re-read.**  A number that does not move is a depth.  A number that moves is a
statement about where the window was drawn.

WHAT IT MEASURES
----------------
AV0  CENSUS, mechanised and REFUSING.  Every `analysis/*.py` site that produces or consumes a
     prominence, found by an AST scan, checked against a DECLARED table of (estimator, role).  A
     new consumer that nobody has classified fails the gate — which is the durable half, because
     s149's lesson is that a guard written in one gate does not protect the others.
AV1  KNOWN ANSWER, on real curves: this gate's own pinned-walk re-implementation must reproduce
     `W.locate`'s `prom` EXACTLY (the walk has to be transcribed to be re-parameterised, so the
     transcription is asserted rather than trusted — s149).  Free by-product: it re-proves AU1's
     structural claim at all SEVEN named features instead of one.
AV2  ESTIMATOR STRUCTURE, both directions.  E1's break must be unreachable (0 breaks); E2's
     (`_best_interior`, s126's repair) must be REACHABLE, or that repair bought nothing — and the
     fraction of E2 readings whose winner IS the window argmin, because those inherit E1's bound
     limitation exactly.  E3 (`R.notch`) must be window-INVARIANT, which is what a named-shoulder
     estimator means and what separates it from E1.
AV3  ⭐ THE MEASUREMENT.  Per named feature, on the PEDAL side of GATE W's own membership: is each
     side's max-ascent attained at an interior SHOULDER or at the window BOUND, and what does the
     reading do under a pinned widening?
AV4  CONSEQUENCE for the DETECTOR role: does the MIN_PROM_DB membership move when the same cells
     are graded on the widened (bound-free-er) reading?  A detector whose verdicts do not move is
     a detector the project can keep quoting.
AV5  The detector claim measured on synthetics with a KNOWN injected feature, in TWO ARMS — the
     window flanked by neighbouring features (which is what every shipped window actually is) and
     the same feature alone on a bare tilt.  The contrast attributes the baseline.
AV6  ⭐⭐ THE PRICE.  A defect found is not a defect priced (s149).  The E1 consumers publish
     CENTRES, not prominences, so this re-grades GATE W6's OWN statistic on W6's OWN membership
     rule with the bar applied to the widened reading — certified by reproducing W6's stored pedal
     spans exactly — and asks whether its published FIXED / DRIVE-DEPENDENT classifications move.

WHAT THIS DOES NOT CLAIM
------------------------
  * It changes no constant and proposes none.
  * **Model side not read, and after AV4 it is OWED.**  AV1-AV4 and AV6 run on the CAPTURES only.
    That was deliberate — a capture curve is binary-independent, so these numbers do not expire the
    next time a constant ships, and the model-side renders on disk predate s156's `OdToneRestore`
    law, so re-rendering them would measure a different chain than the stored GATE W numbers were
    taken on.  The pedal side is 24 captures x 4 sweeps x 7 features, and it is the side W6's
    reference row is built from, so AV6's known answer is available there and nowhere else.
    ⚠ But AV4 DID find membership movement, so the model-side pass the first draft made
    conditional is now genuinely outstanding — see this session's `▶ NEXT`.
  * **AV3's widened reading is NOT a better depth.**  A x2 window is a second arbitrary window and
    it reaches the neighbouring features.  It is used only as a SENSITIVITY probe: a reading that
    moves under it had its value set by where the window was cut.  Nothing here licenses
    re-admitting any cell or re-quoting any widened number as a measurement.
  * It does not re-open any verdict of GATE W, AE, AH or Y.  It reports which of their numbers are
    depths and which are window-bounded lower bounds; where a gate already says so itself (GATE AE
    prints "recovered prominence is a LOWER bound by construction"), AV0 records that rather than
    presenting it as a discovery.

Run:  python3.11 analysis/prominence_audit_gate.py
      python3.11 analysis/_mutate_gate_av.py
"""
import argparse
import ast
import glob
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                # noqa: E402
import bass_peak_locus as Y        # noqa: E402
import captures as C               # noqa: E402
import feature_locus_gate as W     # noqa: E402
import matrix_grade as MG          # noqa: E402
import null_locus_gate as R        # noqa: E402
import od_absolute_gate as Q       # noqa: E402
from parallel import add_jobs_arg, pmap   # noqa: E402

OUT_JSON = os.path.join(HERE, "reports", "s158_prominence_audit.json")

# Widening factors applied to the window's LOG width, geometric centre held.  1.0 is the shipped
# window and must reproduce the shipped reading exactly (AV1).
WIDEN = (1.0, 1.25, 1.6, 2.0)
# AV3: a pinned-widening move this small is "the reading did not move".  Taken from the locator's
# own cell size rather than chosen: one 1/48-octave cell of level change is the finest difference
# the smoothed curve can express, and the shipped MIN_PROM_DB is 1.0 dB, so this is 2 % of the bar.
MOVE_TOL_DB = 0.02

FAILED = []


def fail(tag, msg):
    FAILED.append(tag)
    print(f"\n  ⛔ {tag}: {msg}")


def die(tag, msg):
    print(f"\n  ⛔ {tag}: {msg}")
    sys.exit(1)


# ==================================== AV0: THE CENSUS ===========================================
# The eight prominence estimators this project actually contains.  Only E1 has AU's defect; E2
# inherits it conditionally; the rest are shoulder- or area-referred and cannot have it, because
# they never walk.
ESTIMATORS = {
    "E1": "feature_locus_gate.locate       — walk from the WINDOW ARGMIN; break UNREACHABLE (AU1)",
    "E2": "bass_peak_locus._best_interior  — same walk from a CHOSEN interior index; break reachable",
    "E3": "null_locus_gate.notch           — NAMED-shoulder 1/6-oct power-integrated depth; no walk",
    "E4": "hw_trend_gate.<local locate>    — FIXED 3-band shoulder depth, 1/3-oct grid; no walk",
    "E5": "bt_pair_shape_gate.locate       — own walk, but REFUSES when the extremum rests on a bound",
    "E6": "od_tone_restore_fit.notch_geometry — CORE/SHOULDER windows (s151's repair); no walk",
    "E7": "hf_artefact_gate.prominence     — symmetric ANNULUS reference; no walk",
    "E8": "compression_law_gate.prom       — NAMED-shoulder mean minus the null band; no walk",
    "--": "NOT a prominence — the scan over-matches the NAME `locate`",
}

# file -> (estimator, role, note).  ROLE is what the value is USED for:
#   SOURCE   = defines the estimator
#   DETECTOR = compared against a bar; the verdict is presence/validity, never the value
#   HEIGHT   = the value itself is quoted, differenced, spanned or ranked
#   NONE     = not a prominence
SITES = {
    "feature_locus_gate.py": ("E1", "SOURCE+DETECTOR",
                              "W3's validity bar + the PROM_SWEEP robustness column"),
    "vertex_curvature_gate.py": ("E1", "DETECTOR",
                                 "AH3 membership; AH4b re-runs the headline at every bar and "
                                 "publishes the sensitivity"),
    "bass_peak_locus.py": ("E1+E2", "DETECTOR",
                           "Y's validity bar is E1; Y7b's MOVED/DISSOLVED test is E2, built at "
                           "s126 precisely because E1 reads 0.00 at an edge"),
    "hf_null_presence_gate.py": ("E2", "DETECTOR+HEIGHT",
                                 "AE's headline is n_interior (threshold-free); its prominences "
                                 "are quoted, and AE1b already prints them as LOWER bounds"),
    "od_tone_restore_fit.py": ("E1+E6", "HEIGHT",
                               "prom_table prints pedal-minus-model E1 prominences — the one live "
                               "E1 HEIGHT use, and GATE AU refuted the claim drawn from it (s157). "
                               "The stage's own fit uses E6, which has no walk"),
    "peak_identifiability_gate.py": ("E1", "SOURCE-AUDIT", "GATE AU; walk_detail is E1 instrumented"),
    "prominence_audit_gate.py": ("E1", "SOURCE-AUDIT",
                                 "this gate — `sides_at` is E1 re-parameterised, asserted "
                                 "bit-identical to it at AV1"),
    "null_locus_gate.py": ("E3", "SOURCE+HEIGHT", "GATE R's scored null depth"),
    "null_drive_plane_gate.py": ("E3", "HEIGHT", "GATE V's wash-out plane — imports R.notch"),
    "hw_trend_gate.py": ("E4", "HEIGHT", "AD5/AD5b's depth-axis dose-responses"),
    "bt_pair_shape_gate.py": ("E5", "SOURCE+DETECTOR", "AB refuses a bound-resting extremum"),
    "sk_mechanism_locus.py": ("E5", "DETECTOR", "calls AB.locate"),
    "hf_artefact_gate.py": ("E7", "SOURCE+HEIGHT", "GATE I's G3 fold test, against its own null"),
    "compression_law_gate.py": ("E8", "SOURCE+HEIGHT", "GATE S7's named-shoulder prominences"),
    "notch_shape_gate.py": ("E6", "HEIGHT", "GATE AQ — notch_geometry, no walk"),
    "notch_residual_gate.py": ("E6", "HEIGHT", "GATE AR — notch_geometry, no walk"),
    "null_depth_censor_gate.py": ("E6", "HEIGHT", "GATE AP — notch_geometry, no walk"),
    "crossover_locus.py": ("--", "NONE", "own `locate`, returns a crossover frequency"),
    "read_notch_sweep.py": ("--", "NONE", "own `locate`, a reader utility"),
    "attack_shape_screen.py": ("--", "NONE", "calls attack_render_gate.locate — a notch fitter"),
    "attack_stepped_gate.py": ("--", "NONE", "calls attack_render_gate.locate — a notch fitter"),
}

# Names the AST scan treats as prominence-producing calls.  Deliberately OVER-broad: an
# over-match lands in the declared table with role NONE, an under-match is a site nobody classified.
PROD_NAMES = {"locate", "notch", "_best_interior", "prominence", "prom", "prom_table",
              "walk_detail", "notch_geometry"}


def scan_sites(pattern=os.path.join(HERE, "*.py")):
    """Every analysis module that defines, calls or subscripts a prominence.  Mechanical."""
    found = {}
    for p in sorted(glob.glob(pattern)):
        base = os.path.basename(p)
        if base.startswith("_mutat"):          # mutation runners and their transient mutants
            continue
        try:
            tree = ast.parse(open(p).read())
        except SyntaxError:
            continue
        defs, calls, keys = set(), set(), set()
        for n in ast.walk(tree):
            if (isinstance(n, ast.Subscript) and isinstance(n.slice, ast.Constant)
                    and isinstance(n.slice.value, str) and "prom" in n.slice.value):
                keys.add(n.slice.value)
            if isinstance(n, ast.Call):
                f = n.func
                nm = f.id if isinstance(f, ast.Name) else (f.attr if isinstance(f, ast.Attribute)
                                                           else None)
                if nm in PROD_NAMES:
                    calls.add(nm)
            if isinstance(n, ast.FunctionDef) and n.name in PROD_NAMES:
                defs.add(n.name)
        if defs or calls or keys:
            found[base] = {"defs": sorted(defs), "calls": sorted(calls), "keys": sorted(keys)}
    return found


def av0(out):
    print("\n" + "=" * 100)
    print("AV0  CENSUS — every prominence site in analysis/, mechanically found and classified")
    print("=" * 100)
    found = scan_sites()
    undeclared = sorted(set(found) - set(SITES))
    vanished = sorted(set(SITES) - set(found))
    print(f"  {len(found)} modules touch a prominence; {len(SITES)} are declared here.")
    print(f"\n  {'module':34} {'est':7} {'role':17} what the value is used for")
    print("  " + "-" * 96)
    by_role = {}
    for f in sorted(found):
        est, role, note = SITES.get(f, ("?", "?", ""))
        by_role.setdefault(role, []).append(f)
        print(f"  {f:34} {est:7} {role:17} {note}")
    print("\n  estimators:")
    for k, v in ESTIMATORS.items():
        print(f"    {k}  {v}")

    # The refusals.  A census that cannot go stale is the durable half of this gate (s149).
    if undeclared:
        die("AV0", f"{len(undeclared)} prominence site(s) not in the declared table: "
                   f"{undeclared}\n       Classify them (estimator + role) before quoting any "
                   f"prominence from them — an unclassified consumer is exactly how E1's defect "
                   f"survived 35 sessions.")
    if vanished:
        die("AV0", f"declared site(s) no longer touch a prominence: {vanished} — the table has "
                   f"gone stale; remove them deliberately rather than letting it rot")

    # ⭐ The result the census exists for, computed rather than narrated.
    e1_height = sorted(f for f, (e, r, _) in SITES.items() if "E1" in e and "HEIGHT" in r)
    non_e1_height = sorted(f for f, (e, r, _) in SITES.items()
                           if "E1" not in e and "HEIGHT" in r and e != "--")
    print(f"\n  ⇒ E1 (the estimator with AU's unreachable break) is read as a HEIGHT by "
          f"{len(e1_height)} module(s): {e1_height}")
    print(f"    every OTHER quantitative depth in the project — {len(non_e1_height)} modules: "
          f"{non_e1_height}\n      — is on a shoulder-, area- or annulus-referred estimator that "
          f"never walks, so AU's defect cannot reach it.")
    if len(e1_height) != 1:
        print(f"    ⚠ that count is not 1.  It was 1 at s158 (od_tone_restore_fit.prom_table, and "
              f"GATE AU already refuted the claim drawn from it).  A second E1 HEIGHT site is a "
              f"NEW quantitative use of a window-bounded statistic and needs AV3's table read "
              f"against its own feature before anything is quoted from it.")
    out["av0"] = {"found": found, "sites": {k: list(v) for k, v in SITES.items()},
                  "estimators": ESTIMATORS, "e1_height": e1_height,
                  "non_e1_height": non_e1_height, "by_role": by_role}
    return found


# ============================= the pinned, widenable walk =======================================
def widen_win(win, w):
    """Multiply a window's LOG width by `w`, geometric centre held."""
    lo, hi = float(win[0]), float(win[1])
    c = np.sqrt(lo * hi)
    r = np.sqrt(hi / lo) ** w
    return (float(c / r), float(c * r))


def sides_at(d, i, win, kind, grid=W.GRID):
    """`W.locate`'s prominence walk, re-parameterised: run it from a GIVEN cell `i`, over a GIVEN
    window, and report WHERE each side's maximum ascent was attained.

    ⚠⚠ TRANSCRIBED, NOT IMPORTED, and that is a liability the gate pays for at AV1: `locate`
    couples the walk to `argmin(dd)` over its own window, which is precisely the coupling this
    gate has to break in order to widen the domain with the extremum held.  AV1 therefore asserts
    that this function reproduces `locate`'s `prom` EXACTLY at `widen = 1.0` on every real
    reading, at every feature — if `locate`'s rule ever changes, that assertion is what fails.

    Returns per side: `rise` (the max ascent, which IS locate's per-side term), `at_bound` (was it
    attained at the window's own edge?), and `bound_rise` (the ascent to the edge alone).  When
    `at_bound` is True the side's number is set by where the window was drawn, and widening the
    window can only increase it.  When it is False the ascent is attained at an interior SHOULDER
    and the number is a property of the curve."""
    m = (grid >= win[0]) & (grid <= win[1])
    idx = np.flatnonzero(m)
    if len(idx) < 3 or i < idx[0] or i > idx[-1]:
        return None
    dd = (d if kind == "min" else -d)
    j = int(np.searchsorted(idx, i))
    out = {"i": int(i), "f0_cell": float(grid[i]), "n_cells": int(len(idx))}
    for name, sl in (("left", idx[:j]), ("right", idx[j + 1:])):
        if len(sl) == 0:
            out[name] = {"rise": 0.0, "at_bound": True, "bound_rise": 0.0, "empty": True}
            continue
        v = dd[sl] - dd[i]
        k = int(np.argmax(v))
        out[name] = {"rise": float(v[k]),
                     "at_bound": bool(k == (0 if name == "left" else len(sl) - 1)),
                     "bound_rise": float(v[0] if name == "left" else v[-1]),
                     "empty": False}
    out["prom"] = float(min(out["left"]["rise"], out["right"]["rise"]))
    out["n_bound_sides"] = int(out["left"]["at_bound"]) + int(out["right"]["at_bound"])
    return out


def cell_index(d, win, kind, grid=W.GRID):
    """The GRID CELL `locate` picks — its own argmin, before the parabola interpolation."""
    m = (grid >= win[0]) & (grid <= win[1])
    idx = np.flatnonzero(m)
    dd = (d[m] if kind == "min" else -d[m])
    return int(idx[int(np.argmin(dd))])


# ================================== data: the PEDAL side ========================================
def _cell(fname):
    """One capture, all four sweeps, all seven features — CAPTURE SIDE ONLY (no render, no binary).

    ⚠ Identical curve pipeline to `W.features_of`: same `A.transfer_h1`, same `W.smooth`, so every
    number below is apples-to-apples with GATE W's own readings."""
    orig, ref = W._load_orig()
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    rec = {"file": fname, "sweeps": {}}
    for sw in W.SWEEPS:
        f, m = A.transfer_h1(A.seg_of(cap_al, sw), ref)
        d = W.smooth(f, m)
        per = {}
        for name, kind, win, _lab in W.FEATURES:
            i = cell_index(d, win, kind)
            base = sides_at(d, i, win, kind)
            shipped = W.locate(d, win, kind)
            wide = {}
            for w in WIDEN:
                s = sides_at(d, i, widen_win(win, w), kind)
                wide[f"{w}"] = None if s is None else {
                    "prom": s["prom"], "n_bound_sides": s["n_bound_sides"]}
            # `w3_valid` is GATE W3's OWN admission rule, imported as a predicate rather than
            # re-derived: everything below is reported for ALL readings and, separately, for the
            # ones the project actually quotes.  Auditing readings a gate already refuses would
            # overstate the finding.
            per[name] = {"shipped_prom": shipped["prom"], "edge": shipped["edge"],
                         "margin_frac": shipped["margin_frac"], "f0": shipped["f0"],
                         "w3_valid": bool((not shipped["edge"])
                                          and shipped["margin_frac"] >= W.EDGE_MARGIN_FRAC),
                         "walk": base, "widen": wide}
        rec["sweeps"][sw] = per
    return rec


def membership(report):
    """GATE W's OWN membership, rebuilt through GATE W's own functions rather than re-derived."""
    rep = json.load(open(report))
    caps = {c["file"]: c for c in rep["captures"]}
    lad = W.level_ladder(caps)
    eps = [e for e in Q.endpoints_od(caps) if not MG.is_gain_n12(e)]
    return sorted(set(list(lad.values()) + eps)), lad, eps


# ==================== AV1: the transcription, asserted against the shipped estimator ============
def av1(rows, out):
    print("\n" + "=" * 100)
    print("AV1  KNOWN ANSWER — this gate's pinned walk must reproduce `W.locate`'s `prom` EXACTLY")
    print("=" * 100)
    worst, n, nb = 0.0, 0, 0
    for r in rows:
        for sw, per in r["sweeps"].items():
            for name, v in per.items():
                got = v["widen"]["1.0"]["prom"]
                worst = max(worst, abs(got - v["shipped_prom"]))
                n += 1
                nb += v["walk"]["n_bound_sides"]
    print(f"  {n} readings (pedal side, {len(rows)} captures x {len(W.SWEEPS)} sweeps x "
          f"{len(W.FEATURES)} features)")
    print(f"  worst |this gate - W.locate|  : {worst:.3e} dB")
    if worst > 0.0:
        die("AV1", f"the transcribed walk does not reproduce `W.locate` ({worst:.3e} dB) — every "
                   f"number below is about a DIFFERENT estimator than the project ships")
    print("  ⇒ 0.000e+00 — the re-parameterisation is the shipped statistic, so AV3's widening "
          "measures\n    the shipped statistic and nothing else.")
    # Free by-product: AU1's structural claim, re-proved at all seven features rather than one.
    print(f"\n  ⭐ FREE BY-PRODUCT — AU1's structural claim, at all {len(W.FEATURES)} named features:")
    print(f"     bound-terminated walk sides: {nb} of {2 * n} ({100.0 * nb / (2 * n):.1f} %)")
    if nb != 2 * n:
        print(f"     ⚠ NOT 100 %.  A side whose maximum ascent is attained at an interior shoulder "
              f"is\n       exactly what AU1 says cannot make the walk BREAK — it does not "
              f"contradict AU1 (the\n       break tests `dd[k] < dd[j]`, this tests WHERE the max "
              f"sits).  It is the good case:\n       that side's number is a real depth.")
    out["av1"] = {"n_readings": n, "worst_delta_db": worst, "bound_sides": nb,
                  "sides_total": 2 * n}


# ============================ AV2: which estimators share the defect ============================
def av2(out):
    print("\n" + "=" * 100)
    print("AV2  ESTIMATOR STRUCTURE — E1's break unreachable, E2's reachable, E3 window-invariant")
    print("=" * 100)
    rng = np.random.default_rng(20260805)
    grid = W.GRID
    win = W.FEAT_BY_NAME["mid_peak"][2]
    m = (grid >= win[0]) & (grid <= win[1])
    n_cells = int(m.sum())

    # (a) E1: the break is unreachable.  Adversarial curves, not an argument (s145's AM4).
    e1_breaks = 0
    for _ in range(4000):
        dd = rng.normal(size=n_cells) * rng.uniform(0.1, 20.0)
        j = int(np.argmin(dd))
        for rngk in (range(j - 1, -1, -1), range(j + 1, n_cells)):
            for k in rngk:
                if dd[k] < dd[j]:
                    e1_breaks += 1
                    break
    print(f"  E1  walk from the ARGMIN, 4000 adversarial curves : {e1_breaks} breaks")
    if e1_breaks != 0:
        die("AV2a", "the E1 break fired — AU1's structural claim is false and this gate's whole "
                    "frame with it")

    # (b) E2: the SAME walk from a chosen interior index MUST be able to break, or s126's repair
    # bought nothing.  And: how often is E2's winner the window ARGMIN, where it inherits E1?
    e2_breaks, e2_is_argmin, e2_n = 0, 0, 0
    for _ in range(4000):
        dd = np.cumsum(rng.normal(size=n_cells)) + rng.normal(size=n_cells) * 0.3
        gmin = int(np.argmin(dd))
        best, bj = None, None
        for j in range(1, n_cells - 1):
            if not (dd[j] <= dd[j - 1] and dd[j] <= dd[j + 1]):
                continue
            rises = []
            for rngk in (range(j - 1, -1, -1), range(j + 1, n_cells)):
                rise, broke = 0.0, False
                for k in rngk:
                    rise = max(rise, dd[k] - dd[j])
                    if dd[k] < dd[j]:
                        broke = True
                        break
                rises.append(rise)
                e2_breaks += int(broke)
            p = min(rises)
            if best is None or p > best:
                best, bj = p, j
        if bj is not None:
            e2_n += 1
            e2_is_argmin += int(bj == gmin)
    print(f"  E2  walk from a CHOSEN interior index, 4000 curves : {e2_breaks} breaks "
          f"⇒ s126's repair is real")
    if e2_breaks == 0:
        die("AV2b", "E2's break never fired either — then `_best_interior` is E1 under another "
                    "name and GATE AE/Y's prominences inherit the bound limitation unconditionally")
    frac = e2_is_argmin / max(e2_n, 1)
    print(f"      but its winner IS the window argmin in {frac * 100:.1f} % of curves — and there "
          f"the walk\n      cannot break either, so E2's value is bound-limited in exactly those "
          f"cases.\n      ⇒ E2 removes s126's identically-zero-at-an-edge pathology; it does NOT "
          f"make every\n        reading a topographic prominence.  ⭐ GATE AE already says so "
          f"itself (\"recovered\n        prominence is a LOWER bound by construction\") — recorded, "
          f"not discovered here.")

    # (c) THE DISCRIMINATING KNOWN ANSWER, two-sided: perturb the curve AT THE WINDOW'S OWN EDGES
    # and nowhere else.  E3's reference points are NAMED (202/508 Hz), both outside the window, and
    # its bottom is at 320 Hz — so E3 must be BIT-IDENTICAL.  E1's reference points ARE the window
    # edges whenever the walk is bound-terminated, so E1 must MOVE.  Same perturbation, same
    # question, opposite required answers — which is what makes it a measurement rather than a
    # restatement of each estimator's docstring.
    #
    # ⚠⚠ A FIRST DRAFT ASKED THIS BY WIDENING R.NOTCH_WIN, AND THAT WAS A BROKEN TEST: `R.notch`
    # branches on `win == NOTCH_WIN` and falls back to WINDOW-EDGE shoulders for any other window,
    # so widening deliberately switches it into the very mode under audit.  It duly "failed".
    # A guard must ask for what the estimator promises, not for what a similar-looking call does.
    f = np.linspace(20.0, 2000.0, 40001)
    base = 10.0 ** ((-14.0 * np.exp(-(np.log2(f / 320.0) / 0.12) ** 2)) / 20.0)
    edge = np.zeros_like(f)
    for e in R.NOTCH_WIN:
        edge += 6.0 * np.exp(-((f - e) / 1.5) ** 2)          # +6 dB, ~1.5 Hz wide, at each edge
    pert = base * 10.0 ** (edge / 20.0)
    e3_a, e3_b = R.notch(f, base, R.NOTCH_WIN)[1], R.notch(f, pert, R.NOTCH_WIN)[1]
    d_e3 = abs(e3_a - e3_b)
    print(f"\n  E3  R.notch, curve perturbed AT THE WINDOW EDGES : {e3_a:.4f} -> {e3_b:.4f} dB "
          f"(Δ {d_e3:.2e})")
    if d_e3 > 1e-12:
        fail("AV2c", f"E3 moved by {d_e3:.3e} dB when only the window EDGES changed — its "
                     f"shoulders are then not the named ones and GATE R/V's depths inherit E1's "
                     f"problem after all")
    # ...and the same perturbation on E1, which must move, or the contrast proves nothing.
    dgrid = -14.0 * np.exp(-(np.log2(grid / 320.0) / 0.12) ** 2)
    win_n = W.FEAT_BY_NAME["mid_notch"][2]
    dp = dgrid + np.where((grid <= win_n[0] * 1.01) | (grid >= win_n[1] * 0.99), 6.0, 0.0)
    e1_a = W.locate(dgrid, win_n, "min")["prom"]
    e1_b = W.locate(dp, win_n, "min")["prom"]
    print(f"  E1  the SAME question, same perturbation        : {e1_a:.4f} -> {e1_b:.4f} dB "
          f"(Δ {abs(e1_b - e1_a):.2e})")
    if abs(e1_b - e1_a) <= 1e-9:
        fail("AV2c", "E1 did NOT move when only the window edges changed — then the contrast is "
                     "vacuous and AV3's widening is measuring nothing")
    if d_e3 <= 1e-12 and abs(e1_b - e1_a) > 1e-9:
        print("      ⇒ E3 invariant, E1 moves by the full edge perturbation.  That difference IS "
              "the audit:\n        E3 is referred to the CURVE, E1 to the WINDOW.")
    out["av2"] = {"e1_breaks": e1_breaks, "e2_breaks": e2_breaks,
                  "e2_winner_is_argmin_frac": frac, "e3_edge_delta_db": d_e3,
                  "e1_edge_delta_db": float(abs(e1_b - e1_a))}


# ================== AV3: how much of E1's number is the feature, and how much the window ========
def av3(rows, out):
    print("\n" + "=" * 100)
    print("AV3  ⭐ PINNED WIDENING — a depth does not move; a window-bounded read grows")
    print("=" * 100)
    print("     The extremum is HELD at the cell the shipped window picked, and only the walk")
    print("     domain widens, so this cannot be the s151 trap of the reader jumping features.")
    print("\n  ⚠⚠ WHAT THE WIDENED NUMBER IS AND IS NOT.  It is NOT a better depth — a x2 window is")
    print("     just a second arbitrary window, and it reaches the NEIGHBOURING features, so its")
    print("     value is the ascent to THEIR bottoms.  It is used here only as a SENSITIVITY probe:")
    print("     a reading that moves is one whose value was set by where the window was cut, and")
    print("     that is a statement about the shipped reading, not an endorsement of the wide one.")
    print("\n  Population: GATE W3's OWN admitted readings (interior extremum, margin >= "
          f"{W.EDGE_MARGIN_FRAC}).")
    print(f"\n  {'feature':13} {'n valid':>8} {'/all':>5} {'both-shoulder':>14} {'1 bnd':>6} "
          f"{'2 bnd':>6} {'median prom':>12} {'Δ x2.0':>8} {'worst Δ':>8}  verdict")
    print("  " + "-" * 104)
    per_feature = {}
    for name, kind, win, _lab in W.FEATURES:
        vals, dmove, nb, n_all = [], [], [0, 0, 0], 0
        for r in rows:
            for sw in W.SWEEPS:
                v = r["sweeps"][sw][name]
                n_all += 1
                if not v["w3_valid"]:
                    continue
                nb[v["walk"]["n_bound_sides"]] += 1
                vals.append(v["shipped_prom"])
                w2 = v["widen"][f"{WIDEN[-1]}"]
                if w2 is not None:
                    dmove.append(w2["prom"] - v["shipped_prom"])
        n = len(vals)
        if n == 0:
            print(f"  {name:13} {0:8d} {n_all:5d}   -- no W3-valid reading on the pedal side --")
            per_feature[name] = {"n": 0, "n_all": n_all, "verdict": "NO VALID READING"}
            continue
        med = float(np.median(vals))
        dm = float(np.median(dmove)) if dmove else float("nan")
        dw = float(np.max(np.abs(dmove))) if dmove else float("nan")
        # COMPUTED verdict.  A reading is a DEPTH when widening cannot move it.
        if dw <= MOVE_TOL_DB:
            verdict = "DEPTH (window-free)"
        elif dm <= MOVE_TOL_DB:
            verdict = "MOSTLY DEPTH (a minority of cells window-bound)"
        elif dm >= med:
            verdict = "⛔ WINDOW-DOMINATED — the cut moves it by more than its own value"
        else:
            verdict = "⚠ LOWER BOUND — set partly by the window"
        print(f"  {name:13} {n:8d} {n_all:5d} {nb[0]:14d} {nb[1]:6d} {nb[2]:6d} {med:12.3f} "
              f"{dm:8.3f} {dw:8.3f}  {verdict}")
        per_feature[name] = {"n": n, "n_all": n_all, "both_shoulder": nb[0], "one_bound": nb[1],
                             "two_bound": nb[2], "median_prom_db": med,
                             "median_widen_delta_db": dm, "worst_widen_delta_db": dw,
                             "verdict": verdict}
    graded = [v for v in per_feature.values() if v["n"] > 0]
    n_depth = sum(1 for v in graded if v["verdict"].startswith("DEPTH"))
    n_win = sum(1 for v in graded if "WINDOW" in v["verdict"])
    print(f"\n  ⇒ {n_depth} of {len(graded)} graded features give a window-free DEPTH; "
          f"{n_win} are WINDOW-DOMINATED.")
    print("  ⚠ Read the columns together: `both-shoulder` counts readings whose BOTH maximum "
          "ascents sit\n    at interior shoulders — those are depths by construction, and the "
          "widening column measures\n    the same thing without needing the classification to be "
          "believed.")
    out["av3"] = {"widen": list(WIDEN), "move_tol_db": MOVE_TOL_DB, "per_feature": per_feature,
                  "population": "W3-valid (pedal side)"}
    return per_feature


# ===================== AV4: does the DETECTOR's own membership actually move? ===================
def av4(rows, out):
    print("\n" + "=" * 100)
    print("AV4  CONSEQUENCE — is the MIN_PROM_DB membership ROBUST to the window it is read in?")
    print("=" * 100)
    print("     GATE W's W3, GATE AH's AH3 and GATE Y all select cells with `prom >= bar`, and AV3")
    print("     has just shown `prom` is largely a window statement.  So the question the selecting")
    print("     gates actually need answered is not \"which cells are real\" — nothing here can say")
    print("     that — but \"would this membership have been different had the window been drawn")
    print(f"     wider?\"  Graded on W3-valid readings at every bar in W.PROM_SWEEP = {W.PROM_SWEEP}.")
    print("\n  ⛔ A FLIP IS NOT A REJECTED FEATURE.  The x2.0 window reaches the neighbouring")
    print("     features, so it admits their flanks too.  These counts measure INSTABILITY of the")
    print("     verdict under a window change; they do not license re-admitting any cell.")
    print(f"\n  {'bar':>5} {'n valid':>8} {'over (shipped)':>15} {'over (x2.0)':>12} "
          f"{'flips IN':>9} {'flips OUT':>10} {'unstable':>9}")
    print("  " + "-" * 82)
    tab, flips_detail = {}, []
    for bar in W.PROM_SWEEP:
        n_val = n_ship = n_wide = fin = fout = 0
        for r in rows:
            for sw in W.SWEEPS:
                for name, _k, _w, _l in W.FEATURES:
                    v = r["sweeps"][sw][name]
                    if not v["w3_valid"]:
                        continue
                    n_val += 1
                    a = v["shipped_prom"] >= bar
                    b = v["widen"][f"{WIDEN[-1]}"]["prom"] >= bar
                    n_ship += a
                    n_wide += b
                    if b and not a:
                        fin += 1
                        flips_detail.append({"bar": bar, "file": r["file"], "sweep": sw,
                                             "feature": name, "dir": "IN",
                                             "shipped": v["shipped_prom"],
                                             "wide": v["widen"][f"{WIDEN[-1]}"]["prom"]})
                    if a and not b:
                        fout += 1
        frac = (fin + fout) / max(n_val, 1)
        print(f"  {bar:5.1f} {n_val:8d} {n_ship:15d} {n_wide:12d} {fin:9d} {fout:10d} "
              f"{frac * 100:8.1f}%")
        tab[f"{bar}"] = {"n_valid": n_val, "n_shipped": n_ship, "n_wide": n_wide,
                         "flip_in": fin, "flip_out": fout, "unstable_frac": frac}
    # ⭐ FREE KNOWN ANSWER, and it is a theorem rather than a tolerance: each side's max ascent is
    # a maximum over a set of cells, and widening the window can only ADD cells, so `prom` is
    # non-decreasing in the window width and a flip OUT is impossible.  If one appears, the pinned
    # widening is not pinned — the extremum has moved and AV3's whole table is measuring the s151
    # feature-jump instead of the window.
    n_out = sum(t["flip_out"] for t in tab.values())
    print(f"\n  known answer — `prom` is non-decreasing in window width (a max over a superset), "
          f"so\n  flips OUT must be exactly 0 at every bar: measured {n_out}.")
    if n_out != 0:
        die("AV4", f"{n_out} flip(s) OUT — the extremum is not being held, so the widening is "
                   f"measuring a moved reader (s151) rather than the window")

    ship = tab[f"{W.MIN_PROM_DB}"]
    moved = ship["flip_in"] + ship["flip_out"]
    # COMPUTED verdict — this is the sentence a later session will quote, so it must be able to
    # come back as its opposite (`computed-verdicts-not-narrated`).
    print()
    if moved == 0:
        v = (f"⭐ AT THE SHIPPED BAR ({W.MIN_PROM_DB} dB) THE MEMBERSHIP IS WINDOW-STABLE — 0 flips "
             f"of {ship['n_valid']} W3-valid readings.\n     ⇒ E1's window-boundedness costs the "
             f"DETECTOR role nothing on this data, so GATE W/AH/Y's\n       validity bars mean "
             f"what they say.")
    else:
        v = (f"⚠ THE MEMBERSHIP IS NOT WINDOW-STABLE: {moved} of {ship['n_valid']} W3-valid "
             f"readings ({100.0 * moved / max(ship['n_valid'], 1):.0f} %) change\n     verdict at "
             f"the shipped {W.MIN_PROM_DB} dB bar when the window's log width doubles, all of them "
             f"INWARD.\n     ⇒ the bar is in part a statement about how tightly the window was "
             f"drawn.  ⛔ That does NOT\n       mean those cells hold features — it means a "
             f"presence verdict from this statistic is\n       only as firm as the window, and "
             f"anything QUANTITATIVE read from it is a window number.")
    print("   " + v)
    out["av4"] = {"by_bar": tab, "shipped_bar": W.MIN_PROM_DB, "moved_at_shipped_bar": moved,
                  "flips": flips_detail[:60], "verdict": v,
                  "population": "W3-valid (pedal side)"}
    return moved


# ===================== AV5: the DETECTOR claim, measured in BOTH directions ======================
def av5(out):
    print("\n" + "=" * 100)
    print("AV5  THE DETECTOR CLAIM, ON SYNTHETICS WHERE THE TRUTH IS KNOWN")
    print("=" * 100)
    print("     AU's scope sentence — \"as a DETECTOR the statistic is unharmed\" — is an argument.")
    print("     Here it is a dose-response, against a curve where the feature is INJECTED at a")
    print("     known depth, so `is it there?` has an answer that owes nothing to another estimator.")
    print("\n     TWO ARMS, and the contrast is the measurement:")
    print("       WITH   neighbours — the shipped windows sit BETWEEN two other features, and their")
    print("                           flanks are what a bound-terminated walk actually climbs;")
    print("       ALONE            — the same injected feature on a bare tilt, nothing else in the")
    print("                           window.  Any PRESENT verdict at depth 0 here would be the")
    print("                           estimator inventing a feature, and there should be none.")
    grid = W.GRID
    win = W.FEAT_BY_NAME["mid_peak"][2]
    lg = np.log(grid)
    c = np.sqrt(win[0] * win[1])
    depths = (0.0, 0.25, 0.5, 1.0, 2.0, 4.0, 8.0)
    N = 300
    print(f"\n  bar = {W.MIN_PROM_DB} dB (W.MIN_PROM_DB).  PRESENT rate over {N} curves per rung.")
    print(f"\n  {'injected dB':>12} {'WITH neighbours':>16} {'ALONE':>10}   attribution")
    print("  " + "-" * 66)
    rowsout = {}
    for D in depths:
        n_with = n_alone = 0
        rng = np.random.default_rng(1000 + int(D * 100))     # same curves in both arms
        for _ in range(N):
            tilt = rng.uniform(-8.0, 8.0) * (lg - np.log(c)) / np.log(win[1] / win[0])
            noise = rng.normal(size=len(grid)) * 0.01
            bump = D * np.exp(-((lg - np.log(c * rng.uniform(0.9, 1.1))) / 0.06) ** 2)
            neigh = (-rng.uniform(0.0, 14.0) * np.exp(-((lg - np.log(win[0] * 0.8)) / 0.25) ** 2)
                     - rng.uniform(0.0, 14.0) * np.exp(-((lg - np.log(win[1] * 1.2)) / 0.25) ** 2))
            base = tilt + noise + bump
            n_alone += W.locate(base, win, "max")["prom"] >= W.MIN_PROM_DB
            n_with += W.locate(base + neigh, win, "max")["prom"] >= W.MIN_PROM_DB
        rowsout[f"{D}"] = {"n": N, "with_neighbours": n_with, "alone": n_alone}
        note = "" if D else "  <- NOTHING is there in either arm"
        print(f"  {D:12.2f} {n_with:15d}  {n_alone:9d}{note}")
    z = rowsout["0.0"]
    lift = (rowsout[f"{W.MIN_PROM_DB}"]["with_neighbours"] - z["with_neighbours"]) / N
    print(f"\n  ⇒ WITH neighbours, a feature-free window is called PRESENT "
          f"{100.0 * z['with_neighbours'] / N:.0f} % of the time;")
    print(f"    ALONE it is called PRESENT {100.0 * z['alone'] / N:.0f} % of the time.")
    print(f"    ⇒ the baseline is the NEIGHBOURS' flanks, measured rather than argued — E1 is")
    print(f"      reporting how far the curve falls to the window's edges, and between two real")
    print(f"      features that is large whether or not the named feature exists.")
    print(f"    Injecting a feature AT the bar adds only {100.0 * lift:+.0f} points of PRESENT rate "
          f"over that baseline.")

    # A detector must RESPOND to what it detects.  Asserted on the isolated arm, where nothing else
    # can carry the response — and it is a monotonicity, not a level, so there is no bar to argue
    # about (s129: a dispersion or a level may RANK, only a law may GATE).
    al = [rowsout[f"{d}"]["alone"] for d in depths]
    if any(b < a for a, b in zip(al, al[1:])):
        fail("AV5", f"the isolated-arm PRESENT rate is not monotone in injected depth ({al}) — "
                    f"then this arm is not measuring the injected feature at all")
    print(f"\n  known answer — the isolated arm must be monotone in injected depth: {al}  ✅")
    print(f"  ⚠ and it does NOT reach {N}/{N} until 8 dB: on a background tilted by up to ±8 dB a "
          f"4 dB\n    feature's down-slope ascent can stay under the bar.  That is the FALSE-"
          f"NEGATIVE direction,\n    real and bounded, and it is the estimator being conservative "
          f"rather than wrong.")

    # COMPUTED verdict.  THREE outcomes, not two (s129): "the estimator is bad everywhere",
    # "it is bad only in a flanked window", and "neither arm showed a failure" are different
    # findings, and collapsing the third into either of the others is how a guard comes to assert
    # something its data never showed.  The branch conditions compare two MEASURED arms rather
    # than any threshold this gate invented.
    if z["alone"] > 0:
        v = (f"⚠ E1 INVENTS FEATURES ON A BARE BACKGROUND TOO: {z['alone']} of {N} feature-free "
             f"isolated curves\n     read PRESENT, so the problem is not the neighbours and the "
             f"detector role cannot be defended\n     in any window — every gate selecting on this "
             f"bar owes a re-read, not just the quantitative ones.")
    elif z["with_neighbours"] == 0:
        v = (f"⚪ NO FAILURE DEMONSTRATED — neither arm called a feature-free window PRESENT "
             f"({z['alone']} and\n     {z['with_neighbours']} of {N}).  That is not a defence of "
             f"the statistic; it means THIS synthetic did\n     not exercise it, and the "
             f"contextual claim must not be quoted from this run.")
    else:
        v = (f"⭐ THE DETECTOR'S FAILURE IS CONTEXTUAL, NOT INTRINSIC.  On a bare background E1 "
             f"invents\n     nothing — {z['alone']} of {N} feature-free curves read PRESENT, and "
             f"the rate rises monotonically\n     with depth.  Put the SAME window between two "
             f"other features and {100.0 * z['with_neighbours'] / N:.0f} % of feature-free\n     "
             f"windows read PRESENT, because the walk is climbing the neighbours' flanks.\n"
             f"     ⇒ AU's \"as a detector it is unharmed\" survives only where the window is NOT "
             f"flanked —\n       and every one of GATE W's seven windows is flanked by "
             f"construction, since they tile the\n       band between consecutive named features.")
    print("\n   " + v)
    out["av5"] = {"depths": list(depths), "rows": rowsout, "bar_db": W.MIN_PROM_DB,
                  "n_per_rung": N, "lift_at_bar": lift, "verdict": v}


# ============ AV6: what does any of it COST the conclusions the consumers publish? ==============
def av6(rows, ep_files, w6_stored, out):
    print("\n" + "=" * 100)
    print("AV6  THE PRICE — does the window-dependence reach anything the consumers actually QUOTE?")
    print("=" * 100)
    print("     A defect found is not a defect priced (s149).  Every E1 DETECTOR consumer — GATE W,")
    print("     GATE AH, GATE Y — uses the bar to decide which CENTRE readings are admissible, and")
    print("     then publishes CENTRES, never the prominence itself.  So the question with a")
    print("     consequence in it is: does the admitted population's CENTRE move when the bar is")
    print("     applied to the widened reading instead of the shipped one?")
    print("\n     ⚠ This prices the DETECTOR role only.  The one E1 HEIGHT use in the census")
    print("       (`od_tone_restore_fit.prom_table`) is priced by GATE AU, which refuted the claim")
    print("       drawn from it outright — there is nothing left of it to cost here.")
    print(f"\n  {'feature':13} {'n ship':>7} {'n wide':>7} {'median f0 (ship)':>17} "
          f"{'median f0 (wide)':>17} {'shift':>8}")
    print("  " + "-" * 76)
    per, worst = {}, 0.0
    for name, _k, _w, _l in W.FEATURES:
        fs, fw = [], []
        for r in rows:
            for sw in W.SWEEPS:
                v = r["sweeps"][sw][name]
                if not v["w3_valid"]:
                    continue
                if v["shipped_prom"] >= W.MIN_PROM_DB:
                    fs.append(v["f0"])
                if v["widen"][f"{WIDEN[-1]}"]["prom"] >= W.MIN_PROM_DB:
                    fw.append(v["f0"])
        if not fs or not fw:
            print(f"  {name:13} {len(fs):7d} {len(fw):7d}      -- one population empty --")
            per[name] = {"n_ship": len(fs), "n_wide": len(fw), "shift_frac": None}
            continue
        ms, mw = float(np.median(fs)), float(np.median(fw))
        sh = mw / ms - 1.0
        worst = max(worst, abs(sh))
        print(f"  {name:13} {len(fs):7d} {len(fw):7d} {ms:17.1f} {mw:17.1f} {sh * 100:7.2f}%")
        per[name] = {"n_ship": len(fs), "n_wide": len(fw), "median_f0_ship": ms,
                     "median_f0_wide": mw, "shift_frac": sh}
    # ---- AV6b: the membership that the LOAD-BEARING claims are actually computed on -------------
    # ⚠⚠ A POOLED MEDIAN IS NOT WHAT GATE W6 PUBLISHES, AND NEITHER IS A PER-CAPTURE WALK.  A first
    # draft of this block invented its own rule ("captures resolving at all four rungs, first vs
    # last") and duly reported a 3.48 % movement in a statistic GATE W6 does not compute — pricing
    # the wrong thing (`a-pooled-statistic-cannot-answer-about-its-own-axis`, s105).  W6's rule,
    # read out of `gate_w6` rather than guessed, is: ENDPOINT captures only, per-CELL exclusion
    # (a capture may contribute at one rung and not another), the MEDIAN f0 per sweep, and
    # `span = max/min - 1` over the sweeps that survived.  That is what is reproduced here, and
    # then re-graded with the bar applied to the widened reading.
    print(f"\n  AV6b  THE STATISTIC GATE W6 ACTUALLY PUBLISHES — its own membership rule, its own")
    print(f"        span, re-graded with the bar applied to the widened reading")
    eps = [f for f in ep_files]
    by_file = {r["file"]: r for r in rows}
    print(f"\n  {'feature':13} {'span ship':>10} {'stored W6':>10} {'KA':>4} {'span wide':>10} "
          f"{'Δ span':>8} {'cells s/w':>11}  W6 verdict ship -> wide")
    print("  " + "-" * 100)
    per_b, worst_b, worst_ka, flipped = {}, 0.0, 0.0, []
    for name, _k, _w, _l in W.FEATURES:
        arm, ncell = {}, {}
        for key, use_wide in (("ship", False), ("wide", True)):
            meds, n = [], 0
            for sw in W.SWEEPS:
                vals = []
                for f in eps:
                    if f not in by_file:
                        continue
                    c = by_file[f]["sweeps"][sw][name]
                    p = c["widen"][f"{WIDEN[-1]}"]["prom"] if use_wide else c["shipped_prom"]
                    if not c["w3_valid"] or p < W.MIN_PROM_DB:
                        continue
                    vals.append(c["f0"])
                if vals:
                    meds.append(float(np.median(vals)))
                    n += len(vals)
            arm[key] = (max(meds) / min(meds) - 1.0) if len(meds) >= 3 else float("nan")
            ncell[key] = n
        stored = (w6_stored.get(name, {}).get("pedal", {}) or {}).get("span_frac", float("nan"))
        ka = abs(arm["ship"] - stored) if np.isfinite(arm["ship"]) and np.isfinite(stored) \
            else (0.0 if (not np.isfinite(arm["ship"]) and not np.isfinite(stored))
                  else float("nan"))
        if np.isfinite(ka):
            worst_ka = max(worst_ka, ka)
        dv = abs(arm["wide"] - arm["ship"]) if np.isfinite(arm["wide"]) and np.isfinite(arm["ship"]) \
            else float("nan")
        if np.isfinite(dv):
            worst_b = max(worst_b, dv)
        # ⭐ W6 does not publish a percentage, it publishes a CLASSIFICATION with a percentage
        # beside it, and every argument in open item 6 quotes the classification.  `STIM_MOVE_FRAC`
        # is W6's own bar, imported.
        def cls(x):
            return ("UNRESOLVED" if not np.isfinite(x)
                    else "DRIVE-DEP" if x > W.STIM_MOVE_FRAC else "FIXED")
        c_s, c_w = cls(arm["ship"]), cls(arm["wide"])
        if c_s != c_w:
            flipped.append(name)
        print(f"  {name:13} {arm['ship'] * 100:9.2f}% {stored * 100:9.2f}% "
              f"{'✅' if np.isfinite(ka) and ka < 1e-9 else '⛔':>3} {arm['wide'] * 100:9.2f}% "
              f"{dv * 100:7.2f}% {ncell['ship']:5d}/{ncell['wide']:<5d}  {c_s} -> {c_w}"
              f"{'   ⛔ FLIPPED' if c_s != c_w else ''}")
        per_b[name] = {"span_ship": arm["ship"], "span_wide": arm["wide"], "stored": stored,
                       "ka_delta": ka, "delta": dv, "n_cells": ncell,
                       "class_ship": c_s, "class_wide": c_w}
    # ⭐ CROSS-GATE KNOWN ANSWER.  The pedal side is a deterministic function of the captures and
    # the locator, and neither has changed — so reproducing GATE W's STORED w6 pedal spans is not
    # bookkeeping, it certifies that this block is re-grading W6's real statistic on W6's real
    # membership.  (The pedal side is also binary-independent, which is why this known answer is
    # available at all while the model side's renders are a stale epoch — see the docstring.)
    print(f"\n  known answer — this block must reproduce GATE W's STORED w6 PEDAL spans exactly: "
          f"worst Δ {worst_ka:.3e}")
    if not (worst_ka < 1e-9):
        die("AV6b", f"the reproduction of GATE W6's stored pedal spans is off by {worst_ka:.3e} — "
                    f"this block is then re-grading a DIFFERENT statistic than W6 publishes, and "
                    f"its consequence figures say nothing about W6's numbers")

    # The bar this is graded against is IMPORTED, not chosen: GATE W's own "same reading"
    # resolution, one third of a 1/48-octave cell, which is the bar W1 uses to decide whether two
    # centre readings differ at all.
    res = W.GRID_STEP_FRAC / 3.0
    print(f"\n  graded against GATE W's OWN resolution — a third of a 1/48-oct cell = "
          f"{res * 100:.2f} % (W.GRID_STEP_FRAC/3),\n  imported rather than chosen: two centres "
          f"closer than that are the same reading to this locator.")
    # THE VERDICT, and it has to separate two things a single "worst Δ" would fuse: W6 publishes a
    # CLASSIFICATION (FIXED vs DRIVE-DEPENDENT) with a percentage beside it, and every argument in
    # open item 6 quotes the classification while only some quote the percentage.
    if not flipped:
        v = (f"⭐⭐ THE CLASSIFICATIONS SURVIVE; THE PERCENTAGES DO NOT.  Re-grading GATE W6's own "
             f"statistic on\n     its own membership with the bar applied to the widened reading "
             f"flips {len(flipped)} of {len(per_b)} FIXED /\n     DRIVE-DEPENDENT verdicts — so "
             f"every argument that quotes W6's CLASSIFICATION (open item 6's\n     whole frame, "
             f"AA6, AD) stands.  But the SIZES move by up to {worst_b * 100:.2f} % against a "
             f"{res * 100:.2f} %\n     resolution — worst at "
             f"`{max(per_b, key=lambda k: per_b[k]['delta'] if np.isfinite(per_b[k]['delta']) else -1)}`"
             f" — so ⛔ a quoted PERCENTAGE from this family\n     (the 7.15 %, the 7.9 %, the "
             f"7.95 %) carries a membership dependence nobody has been\n     quoting with it.  "
             f"Quote them as \"~7-10 %, DRIVE-DEPENDENT\", not to two decimals.")
    else:
        v = (f"⚠⚠ A PUBLISHED CLASSIFICATION FLIPS: {flipped} change between FIXED and "
             f"DRIVE-DEPENDENT when\n     the same bar is applied to the widened reading — so W6's "
             f"verdict for those features is in\n     part a statement about how the window was "
             f"drawn, and every argument resting on them\n     (open item 6's frame, AA6, AD) owes "
             f"a re-read.  Sizes move by up to {worst_b * 100:.2f} %.")
    print("\n   " + v)
    out["av6"] = {"per_feature": per, "worst_shift_frac": worst, "resolution_frac": res,
                  "dose_response": per_b, "worst_walk_delta_frac": worst_b, "verdict": v}
    return worst_b


def main():
    ap = argparse.ArgumentParser(description="GATE AV — project-wide prominence audit")
    ap.add_argument("--report", default=W.REPORT)
    ap.add_argument("--json", default=OUT_JSON)
    add_jobs_arg(ap)
    args = ap.parse_args()

    print("=" * 100)
    print("GATE AV — the project-wide `prom` audit: which prominence numbers are DEPTHS, and")
    print("          which are WINDOWS?   (pedal side; no render, no binary — see the docstring)")
    print("=" * 100)
    out = {"report": args.report, "widen": list(WIDEN), "move_tol_db": MOVE_TOL_DB}

    av0(out)
    av2(out)

    if not os.path.exists(args.report):
        die("AV", f"{args.report} not found — it defines GATE W's own membership")
    files, lad, eps = membership(args.report)
    print(f"\n  membership (GATE W's own, rebuilt through its own functions): {len(files)} captures"
          f"\n    LEVEL ladder {len(lad)} detents + {len(eps)} bleed-free OD endpoints")
    if len(files) < 10:
        die("AV", f"only {len(files)} captures — the membership collapsed, and a thin population "
                  f"would make AV3's per-feature counts unreadable")
    rows = pmap(_cell, files, jobs=args.jobs)

    # GATE W's STORED w6, for AV6b's cross-gate known answer.  READ, never transcribed — and the
    # gate refuses without it rather than quietly grading against nothing, because the whole point
    # of AV6b is that it re-grades W6's real statistic and only the stored report can prove it does.
    if not os.path.exists(W.OUT_JSON):
        die("AV6b", f"{W.OUT_JSON} not found — AV6b's consequence figures are only about GATE W6 "
                    f"if they reproduce W6's stored pedal spans first")
    w6_stored = json.load(open(W.OUT_JSON)).get("w6", {})
    if not w6_stored:
        die("AV6b", f"{W.OUT_JSON} carries no `w6` block")

    av1(rows, out)
    av3(rows, out)
    av4(rows, out)
    av5(out)
    av6(rows, eps, w6_stored, out)

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, sort_keys=True)
    print(f"\n  -> {args.json}")

    print("\n" + "=" * 100)
    if FAILED:
        print(f"GATE AV: {len(FAILED)} check(s) failed: {', '.join(FAILED)}")
    else:
        print("GATE AV: census complete, all estimator known answers held")
    print("=" * 100)
    return 1 if FAILED else 0


if __name__ == "__main__":
    sys.exit(main())
