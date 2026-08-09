#!/usr/bin/env python3.11
"""GATE BP — DOES `OdDriveTilt` STILL DELIVER AT A **PLAYED** SETTING?  (session 188, item 19's P4)

WHY THIS EXISTS
---------------
`OdDriveTilt` (s166) shipped on GATE BC's acceptance table, and **every cell of that table is
bleed-free** — BC0 asserts `level == 1.0` on all five of its conditions and exits if not.  Item 19's
task P4 is to re-read that acceptance at the mix, for the reason the user gave at s173:

    *"ONLY looking at bleed free for literally anything breaks ANY setting that isn't level1700 ...
      `ref-od` should be the starting reference, NEVER the bleed free one."*

There is a specific mechanism to worry about, and it is not subtle.  The stage sits in the OD
branch, UPSTREAM of `LevelBlend`; at a mixed setting its output is summed with a clean tap that it
cannot touch.  So whatever it does to the OD branch arrives at the output DILUTED by that branch's
share — and the share is itself rung-dependent, because the OD path compresses with stimulus and the
clean tap does not.  The graded quantity here (a drive-tilt, i.e. a DIFFERENCE between rungs) is
therefore diluted by a factor that itself moves across the very axis being measured.

⭐⭐ THIS GATE IS DELIBERATELY SELF-CONTAINED, AND THAT IS A FINDING, NOT A STYLE CHOICE.
GATE BC imports its requirement through `drive_tilt_shape_gate.load_af6()` →
`analysis/reports/s134_sk_mechanism.json` → `analysis/reports/s122_feature_locus.json`.  Both are
**gitignored and absent**, and the tool that regenerates the second one renders into
`build/s122_feature_locus/` — GATE W's READ-ONLY cache, whose 25 entries all carry a binary stamp
that no longer matches the shipped binary, so `W.render` would re-render every one of them and
destroy the s122 epoch that GATEs AV / AW / AF / AG / BC all read.  ⇒ **GATE BC cannot be re-run on
the current build without paying that price**, so this gate imports no report at all: the
requirement is MEASURED per cell, from the captures, as `pedal − model(tilt OFF)`.

WHAT IS GRADED, AND WHY IT IS THE HONEST FORM
  * The DELIVERY (`ON − OFF` at one cell) isolates the stage exactly: both arms share the cell, so
    the mix coefficients, `OdToneRestore`'s mix-keyed cut (s156) and every other mix-dependent term
    are IDENTICAL between them and cancel.  This is what BC graded, and it is re-graded here across
    the mix.
  * The REQUIREMENT is re-measured at each cell as `pedal − model(OFF)`, because at a mixed cell
    BOTH sides carry a clean tap, so the deficit the stage is supposed to close is itself diluted.
    Comparing a bleed-free requirement against a mixed delivery would be two different quantities
    (`difference-statistics-hide-common-mode`), which is exactly the trap this gate exists to avoid.
  * ⇒ the headline is a RATIO of two quantities measured at the same cell — the CLOSURE — and
    BC's own headline (*"delivers 0.99x the requirement"*) is the comparand.

WHAT THIS DOES NOT CLAIM
  * It does not price the matrix.  That is `comprehensive_report.py`.
  * It proposes no change to the stage.  A delivery that falls with clean fraction is a PROPERTY of
    where the stage sits, not a defect of its coefficients, and whether it should be compensated is
    a USER decision with its own price.
  * Both sides are the ND captures (`reference-sources.md` §0); §1 gives this region to neither
    reference outright, so nothing here is graded against hardware.
  * ⚠ Renders at `--os 8` (GATE W's factor, imported), where the shipped OS gate turns ADAA OFF —
    the same standing caveat every matrix number carries.

Usage:
  python3.11 analysis/od_tilt_mix_gate.py
  python3.11 analysis/od_tilt_mix_gate.py --json analysis/reports/s188_od_tilt_mix.json
"""
import argparse
import json
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                        # noqa: E402
import captures as C                       # noqa: E402
import feature_locus_gate as W             # noqa: E402  GRID / smooth / locate / render / REN_DIR
import task_e_placement_gate as BA         # noqa: E402  slope(), drive_tilt(), fingerprint(), HALF
import drive_tilt_shape_gate as AG         # noqa: E402  RUNGS, INJECT_TOL — imported, not re-derived
import mix_anchor_reanchor_gate as BN      # noqa: E402  clean_frac() — GATE K's mirrors, end-stop aware

# ⛔⛔ PRIVATE render directory.  NEVER `build/s122_feature_locus/` (s159 AW0): that cache holds the
# artefacts GATE W published from, `W.render` re-renders anything whose binary stamp is stale, and
# every one of its stamps IS stale.  BP0 asserts the two paths differ and fingerprints W's.
PRIV_DIR = os.path.join(os.path.dirname(HERE), "build", "s188_od_tilt_mix")

RUNGS = AG.RUNGS
JOBS = max(1, min(8, (os.cpu_count() or 4) - 2))

# ------------------------------------------------------------------------------------------------
# MEMBERSHIP.  Every cell is a REAL capture on disk, so the pedal side of BP3/BP4 is a measurement
# and not a model of one.  GRUNT cut and ATTACK flat throughout (the untokened default, s151's
# trap), DRIVE noon except where the label says otherwise.  (LEVEL, BLEND) is the mix axis.
# ------------------------------------------------------------------------------------------------
CELLS = (
    # label                    file                                  L      B
    ("L1.000/B1.00",           "level-1700_base-od.wav",             1.000, 1.00),   # BC's own cell
    ("L0.875/B1.00",           "level-1545_base-od.wav",             0.875, 1.00),
    ("L0.750/B1.00",           "level-1430_base-od.wav",             0.750, 1.00),
    ("L0.625/B1.00",           "level-1315_base-od.wav",             0.625, 1.00),
    ("L0.500/B1.00 *PLAY*",    "ref-od.wav",                         0.500, 1.00),   # the reference
    ("L0.375/B1.00",           "level-1045_base-od.wav",             0.375, 1.00),
    ("L0.250/B1.00",           "level-0930_base-od.wav",             0.250, 1.00),
    ("L1.000/B0.75",           "level-1700_blend-1430_base-od.wav",  1.000, 0.75),
    ("L1.000/B0.50",           "level-1700_blend-1200_base-od.wav",  1.000, 0.50),
    ("L1.000/B0.25",           "level-1700_blend-0930_base-od.wav",  1.000, 0.25),
    ("L0.500/B1.00 DRIVEmin",  "drive-0700_base-od.wav",             0.500, 1.00),
    ("L0.500/B1.00 DRIVEmax",  "drive-1700_base-od.wav",             0.500, 1.00),
)
CORNER = "L1.000/B1.00"
PLAY = "L0.500/B1.00 *PLAY*"

# Scope controls: two settings the stage is ARCHITECTURALLY unable to reach.
SCOPE = (("BLEND min (OD out of circuit)", "blend-0700_base-od.wav"),
         ("CLEAN path", "ref-clean.wav"))

MIN_DELIVERY_DB_OCT = 0.05   # BP1d non-vacuity: the corner must move by at least this
FAILED = []


def die(tag, msg):
    sys.exit(f"GATE BP {tag} FAIL: {msg}")


def note(tag, msg):
    FAILED.append(f"{tag}: {msg}")
    print(f"   ** {tag} FAIL — {msg}")


# ------------------------------------------------------------------------------------------------
# curves
# ------------------------------------------------------------------------------------------------
def render_path(fname, on):
    return os.path.join(PRIV_DIR,
                        fname.replace(".wav", "") + ("_on" if on else "_off") + "_plugin.wav")


def do_render(job):
    fname, on = job
    W.render(render_path(fname, on),
             list(C.render_args(C.parse_capture(fname))) + ["--fit", f"odTiltEnabled={1 if on else 0}"])


def model_curves(fname, on):
    """{rung: dB on W.GRID} for the MODEL at one cell and one arm."""
    orig, ref = W._load_orig()
    al, _ = A.align(A.load(render_path(fname, on)), orig)
    return {sw: W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)) for sw in RUNGS}


def pedal_curves(fname):
    """{rung: dB on W.GRID} for the PEDAL (the capture), through the identical pipeline."""
    orig, ref = W._load_orig()
    al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    return {sw: W.smooth(*A.transfer_h1(A.seg_of(al, sw), ref)) for sw in RUNGS}


def valid(r):
    """GATE W's OWN validity rule for a located reading, imported rather than restated."""
    return (not r["edge"]) and r["margin_frac"] >= W.EDGE_MARGIN_FRAC and r["prom"] >= W.MIN_PROM_DB


# ------------------------------------------------------------------------------------------------
# BP0 — membership, provenance, cache guard
# ------------------------------------------------------------------------------------------------
def bp0(out):
    print("=" * 100)
    print("BP0  MEMBERSHIP, PROVENANCE, CACHE GUARD")
    if os.path.abspath(PRIV_DIR) == os.path.abspath(W.REN_DIR):
        die("BP0", "the private render directory IS GATE W's cache — refusing to render into it.")

    files = [f for _l, f, _L, _B in CELLS] + [f for _l, f in SCOPE]
    missing = [f for f in files if not os.path.exists(os.path.join(C.CAPTURE_DIR, f))]
    if missing:
        die("BP0", f"{len(missing)} capture(s) absent, so the membership is not the stated one: "
                   f"{missing}")
    if len(set(f for _l, f, _L, _B in CELLS)) != len(CELLS):
        die("BP0", "a capture is doing duty for two cells — the mix axis is not the stated one.")

    # Every cell must BE the (LEVEL, BLEND) its label claims, resolved from SETTINGS (s114).
    rows = {}
    for lab, f, L, B in CELLS:
        p = C.parse_capture(f)
        if abs(p["level"] - L) > 1e-9 or abs(p["blend"] - B) > 1e-9:
            die("BP0", f"{f} is LEVEL={p['level']} BLEND={p['blend']}, not the labelled "
                       f"({L}, {B}) — the mix axis is mislabelled.")
        if p.get("gruntIdx") != 1 or p.get("attackIdx") != 0:
            die("BP0", f"{f} is not the GRUNT-cut / ATTACK-flat baseline "
                       f"(grunt={p.get('gruntIdx')}, attack={p.get('attackIdx')}) — s151's trap.")
        rows[lab] = {"file": f, "level": L, "blend": B, "drive": p["drive"],
                     "cf": BN.clean_frac(L, B)}

    print(f"   private render dir : {PRIV_DIR}")
    print(f"   GATE W cache       : {W.REN_DIR}  (READ-ONLY here, fingerprinted before and after)")
    print(f"   cells              : {len(CELLS)}, every one a real capture, GRUNT cut / ATTACK flat")
    print(f"   OS factor          : {W.OS_FACTOR} (imported from GATE W — the ADAA gate is OFF there)")
    print()
    print(f"   {'cell':26s}{'DRIVE':>7s}{'cleanFraction':>15s}   capture")
    for lab, _f, _L, _B in CELLS:
        r = rows[lab]
        print(f"   {lab:26s}{r['drive']:7.2f}{r['cf']:15.5f}   {r['file']}")
    cfs = [rows[lab]["cf"] for lab, _f, _L, _B in CELLS]
    print(f"\n   clean fraction spans {min(cfs):.5f} .. {max(cfs):.5f} — the DOSE axis of BP2")
    print(f"   ⚠ the corner's cf is {rows[CORNER]['cf']:.5f}, NOT 0: `blendEndStop` (s181) put a")
    print( "     clean term at the bleed-free corner, so even BC's own cell now carries bleed.")

    # ⭐ The stale-import finding, MEASURED rather than asserted: how much of GATE W's read-only
    # cache would be re-rendered if the BC import chain were regenerated on this binary.
    stale = fresh = 0
    for n in sorted(os.listdir(W.REN_DIR)) if os.path.isdir(W.REN_DIR) else []:
        if not n.endswith(".args.json"):
            continue
        try:
            d = json.load(open(os.path.join(W.REN_DIR, n)))
        except (OSError, ValueError):
            continue
        if d.get("bin") == W._bin_sig():
            fresh += 1
        else:
            stale += 1
    print(f"\n   GATE W cache stamps: {fresh} match the shipped binary, {stale} are STALE")
    if stale:
        print( "   ⛔ ⇒ regenerating GATE BC's import chain (W -> AF -> AG) on this build would")
        print(f"     RE-RENDER {stale} entries INTO the read-only cache and destroy the s122 epoch.")
        print( "     That is why this gate imports no report and measures its requirement per cell.")
    out["bp0"] = {"cells": rows, "w_cache_stale": stale, "w_cache_fresh": fresh,
                  "os_factor": W.OS_FACTOR}
    return rows


# ------------------------------------------------------------------------------------------------
# BP1 — known answers
# ------------------------------------------------------------------------------------------------
def bp1(mod_off, mod_on, vertex, out):
    print()
    print("=" * 100)
    print("BP1  KNOWN ANSWERS")
    rec = {}

    # (a) the estimator recovers an INJECTED tilt exactly, including ZERO (the arm's own control).
    base = mod_off[CORNER][RUNGS[0]]
    rows = []
    for T in (0.0, -0.5, 1.0, -2.5):
        got = BA.slope(base + T * np.log2(W.GRID / vertex), vertex) - BA.slope(base, vertex)
        rows.append((T, got))
    worst = max(abs(g - T) for T, g in rows)
    print(f"   (a) injected-tilt recovery at {vertex:.1f} Hz "
          f"(exact algebra, so the bar is machine precision):")
    for T, g in rows:
        tag = "   <- ZERO: this arm's own mutation control" if T == 0.0 else ""
        print(f"        injected {T:+7.3f}  recovered {g:+7.3f}  |err| {abs(g - T):.2e}{tag}")
    if worst > AG.INJECT_TOL:
        die("BP1a", f"the tilt estimator recovers an injected tilt to only {worst:.2e} dB/oct.")
    rec["inject_worst"] = worst

    # (b/c) SCOPE — two settings the stage cannot architecturally reach.  BIT-IDENTICAL, or the
    # ON-minus-OFF difference at every mixed cell is not attributable to the OD branch.
    print("   (b) ⭐ SCOPE — settings the stage is architecturally unable to reach must be "
          "BIT-IDENTICAL:")
    worst_s, n_s = 0.0, 0
    for lab, f in SCOPE:
        a, b = A.load(render_path(f, False)), A.load(render_path(f, True))
        n = min(len(a), len(b))
        if n == 0:
            die("BP1b", f"{f} rendered to an empty file — the scope control measured nothing.")
        d = float(np.max(np.abs(a[:n] - b[:n])))
        worst_s = max(worst_s, d)
        n_s += 1
        print(f"       {lab:34s} {f:26s} max |on - off| = {d:.3e}  over {n} samples")
    # ⛔ BOTH halves are needed.  `n_s != len(SCOPE)` alone is satisfied by 0 == 0, so an EMPTY
    # scope set would sail through the check written to catch an untested one (`empty-gate-must-fail`
    # in the one place it is invisible — found by this gate's own mutation runner).
    if n_s == 0 or n_s != len(SCOPE):
        die("BP1b", f"only {n_s} of {len(SCOPE)} scope control(s) ran — an untested scope control "
                    f"is a refusal, not a pass.")
    if worst_s != 0.0:
        note("BP1b", f"a scope control is NOT bit-identical ({worst_s:.3e}) — the stage is "
                     f"reaching a path it cannot be in, and every delivery number below is "
                     f"unattributable.")
    else:
        print(f"       ⇒ BIT-IDENTICAL on {n_s}/{n_s} — the stage is confined to the OD branch")
    rec["scope_worst"] = worst_s

    # (d) NON-VACUITY — ON must actually move the OD render, at the corner AND at the play cell.
    print("   (d) non-vacuity — `--fit odTiltEnabled` must genuinely switch the stage:")
    nv = {}
    for lab in (CORNER, PLAY):
        d = max(float(np.max(np.abs(mod_on[lab][sw] - mod_off[lab][sw]))) for sw in RUNGS)
        t = abs(BA.drive_tilt(mod_on[lab], vertex) - BA.drive_tilt(mod_off[lab], vertex))
        nv[lab] = [d, t]
        print(f"       {lab:26s} worst |ON - OFF| = {d:7.3f} dB   |delta drive-tilt| = "
              f"{t:.4f} dB/oct")
    if nv[CORNER][1] < MIN_DELIVERY_DB_OCT:
        die("BP1d", f"the stage moves the corner's drive-tilt by only {nv[CORNER][1]:.3e} dB/oct — "
                    f"every ratio below would be dividing one nothing by another "
                    f"(`ratio-statistics-need-a-denominator-guard`).")
    rec["nonvacuity"] = nv

    # (e) ⭐⭐ THE LICENCE FOR READING `ON - OFF` AS "THE STAGE, DILUTED": the envelope follower is
    # MIX-INVARIANT BY CONSTRUCTION.  Asserted on the SOURCE, because it is a property of where the
    # tap is, not of any number this gate can render (the AN1b idiom, s148).
    src = open(os.path.join(os.path.dirname(HERE), "src", "dsp", "PedalChain.h")).read()
    calls = re.findall(r"odDriveTilt\.(\w+)\s*\(([^;]*)\)\s*;", src)
    if not calls:
        die("BP1e", "no `odDriveTilt.` call sites found in PedalChain.h — the source assertion "
                    "matched nothing, which is `empty-gate-must-fail`, not a pass.")
    banned = ("level", "blend", "cleanFrac", "cleanfrac", "mix")
    bad = [(m, a) for m, a in calls if any(b.lower() in a.lower() for b in banned)]
    print(f"   (e) ⭐ envelope tap is MIX-INVARIANT — {len(calls)} `odDriveTilt.` call site(s) in "
          f"PedalChain.h:")
    for m, a in calls:
        print(f"       .{m}({a.strip()[:64]})")
    if bad:
        die("BP1e", f"a LEVEL/BLEND/mix-derived quantity reaches the stage: {bad}.  The follower "
                    f"would then depend on the mix, and `ON - OFF` could not be read as one "
                    f"fixed OD-branch change seen through different amounts of dilution.")
    print("       ⇒ no LEVEL/BLEND/mix-derived term reaches the stage, so its OD-branch change is")
    print("         the SAME at every cell and `ON - OFF` measures that change DILUTED, nothing else")
    rec["call_sites"] = [f".{m}" for m, _a in calls]
    out["bp1"] = rec


# ------------------------------------------------------------------------------------------------
# BP2 — the delivery, as a dose-response in clean fraction
# ------------------------------------------------------------------------------------------------
def bp2(mod_off, mod_on, cells, vertex, out):
    print()
    print("=" * 100)
    print("BP2  ⭐ DELIVERY vs CLEAN FRACTION — what the stage actually puts into the output")
    print(f"   drive-tilt = slope({RUNGS[-1]}) - slope({RUNGS[0]}) at {vertex:.1f} Hz, GATE AG's")
    print("   estimator.  BOTH operands printed, never the difference alone (s117).")
    print()
    print(f"   {'cell':26s}{'cf':>9s}{'OFF':>10s}{'ON':>10s}{'delivered':>12s}{'re corner':>11s}")
    rows = {}
    for lab, _f, _L, _B in CELLS:
        a = BA.drive_tilt(mod_off[lab], vertex)
        b = BA.drive_tilt(mod_on[lab], vertex)
        rows[lab] = {"off": a, "on": b, "delivered": b - a, "cf": cells[lab]["cf"]}
    ref = rows[CORNER]["delivered"]
    for lab, _f, _L, _B in CELLS:
        r = rows[lab]
        r["re_corner"] = r["delivered"] / ref if abs(ref) > 1e-12 else float("nan")
        print(f"   {lab:26s}{r['cf']:9.4f}{r['off']:+10.4f}{r['on']:+10.4f}"
              f"{r['delivered']:+12.4f}{r['re_corner']:10.2f}x")

    # The dose-response, on the LEVEL ladder at BLEND max — the one axis that moves cf alone.
    ladder = [lab for lab, _f, _L, B in CELLS if B == 1.00 and "DRIVE" not in lab]
    ladder.sort(key=lambda x: rows[x]["cf"])
    seq = [rows[l]["delivered"] for l in ladder]
    mono = all(abs(seq[i + 1]) <= abs(seq[i]) + 1e-9 for i in range(len(seq) - 1))
    print(f"\n   LEVEL ladder at BLEND max, ordered by clean fraction ({len(ladder)} cells):")
    print("      cf       " + "".join(f"{rows[l]['cf']:9.3f}" for l in ladder))
    print("      delivered" + "".join(f"{rows[l]['delivered']:+9.3f}" for l in ladder))
    arg = int(np.argmax([abs(s) for s in seq]))
    # ⭐ COMPUTED shape verdict — the DIRECTION is derived, never narrated (s184).
    if mono:
        print("   ⇒ |delivery| FALLS MONOTONICALLY with clean fraction — simple dilution")
    elif arg in (0, len(seq) - 1):
        print(f"   ⇒ |delivery| is NOT monotone, and its extreme is at a SAMPLING EDGE "
              f"(cf {rows[ladder[arg]]['cf']:.3f}) — an extremum at an edge is not a measurement "
              f"of the extremum (s184)")
    else:
        print(f"   ⇒ |delivery| is NOT monotone: it PEAKS at an INTERIOR mix "
              f"(cf {rows[ladder[arg]]['cf']:.3f}, {abs(seq[arg]):.3f} dB/oct) and falls away on "
              f"both sides")
        print("     ⭐ Dilution alone cannot do that.  The dilution factor is itself RUNG-DEPENDENT")
        print("       (the OD branch compresses with stimulus and the clean tap does not), so the")
        print("       mix adds a SECOND rung-dependence on top of the stage's own — and a")
        print("       drive-tilt is a difference between rungs, so the two can ADD.")
    play, corner = rows[PLAY]["delivered"], rows[CORNER]["delivered"]
    frac = abs(play / corner) if abs(corner) > 1e-12 else float("nan")
    print(f"\n   ⭐ At the PLAY cell the stage delivers {play:+.4f} dB/oct against the corner's "
          f"{corner:+.4f} — {frac * 100:.0f} %.")
    out["bp2"] = {"rows": rows, "ladder": ladder, "monotone": bool(mono),
                  "argmax_cf": rows[ladder[arg]]["cf"], "argmax_edge": arg in (0, len(seq) - 1)}
    return rows


def bp2b(mod_off, mod_on, ped, out):
    """The same two quantities across FREQUENCY — so no conclusion rests on one read point."""
    print()
    print("-" * 100)
    print("BP2b ROBUSTNESS — delivered and required ACROSS the interpretable band")
    print(f"   Band bounds IMPORTED from GATE W's own feature windows: "
          f"{BA.SMOOTH_LO:.0f} .. {BA.SMOOTH_HI:.0f} Hz (above `bt_notch`, below `treble_notch`),")
    print("   so no centre's fit window reaches a neighbouring migrating feature (AG's rule).")
    fs = [f for f in (1200.0, 1600.0, 2100.0, 2714.0, 3400.0)
          if BA.SMOOTH_LO <= f <= BA.SMOOTH_HI]
    print()
    print(f"   {'cell':26s}" + "".join(f"{f:>9.0f}" for f in fs) + "   <- delivered (ON - OFF)")
    rows = {}
    for lab, _f, _L, _B in CELLS:
        d = [BA.drive_tilt(mod_on[lab], f) - BA.drive_tilt(mod_off[lab], f) for f in fs]
        r = [BA.drive_tilt(ped[lab], f) - BA.drive_tilt(mod_off[lab], f) for f in fs]
        rows[lab] = {"f": fs, "delivered": d, "required": r}
        print(f"   {lab:26s}" + "".join(f"{x:+9.3f}" for x in d))
    print()
    print(f"   {'cell':26s}" + "".join(f"{f:>9.0f}" for f in fs) + "   <- required (PEDAL - OFF)")
    for lab, _f, _L, _B in CELLS:
        print(f"   {lab:26s}" + "".join(f"{x:+9.3f}" for x in rows[lab]["required"]))

    mixed = [lab for lab, _f, _L, _B in CELLS if lab != CORNER]
    # ⛔ PER CENTRE, never pooled: pooling a SIGN over frequency is
    # `a-pooled-statistic-cannot-answer-about-its-own-axis`, and here the axis IS the answer.
    per = {f: sum(1 for lab in mixed if rows[lab]["required"][i] > 0) for i, f in enumerate(fs)}
    npos, ntot = sum(per.values()), len(mixed) * len(fs)
    cpos = sum(1 for x in rows[CORNER]["required"] if x > 0)
    print(f"\n   ⚠ SIGN is the whole point: `required` > 0 means the model's composite is ALREADY")
    print("     MORE drive-tilted than the pedal's, so a correction that adds negative tilt is")
    print("     pushing the WRONG WAY at that cell.")
    print(f"\n   mixed cells with required > 0, PER CENTRE (n = {len(mixed)} each):")
    for f in fs:
        print(f"      {f:7.0f} Hz : {per[f]:2d} / {len(mixed)}")
    print(f"   corner: required is POSITIVE at {cpos} of {len(fs)} centres")
    unan = [f for f in fs if per[f] == len(mixed)]
    none_ = [f for f in fs if per[f] == 0]
    if unan:
        print(f"   ⇒ UNANIMOUSLY positive at {', '.join(f'{f:.0f}' for f in unan)} Hz — at and above")
        print("     the vertex the model is already over-tilted at EVERY mixed cell")
    if none_:
        print(f"   ⇒ and unanimously NEGATIVE at {', '.join(f'{f:.0f}' for f in none_)} Hz")
    print("   ⛔ ⇒ the sign is FREQUENCY-DEPENDENT, so quote the centre with it.  `the model is")
    print("     already over-tilted` is a statement about the upper half of this band, not the band.")
    out["bp2b"] = {"freqs": fs, "rows": rows, "per_centre_positive": {str(k): v for k, v in per.items()},
                   "n_mixed": len(mixed), "mixed_positive": npos, "mixed_total": ntot,
                   "corner_positive": cpos, "corner_total": len(fs),
                   "unanimous_positive_hz": unan}


# ------------------------------------------------------------------------------------------------
# BP3 — the acceptance re-read: closure against a requirement measured AT THE SAME CELL
# ------------------------------------------------------------------------------------------------
def bp3(mod_off, ped, deliv, vertex, out):
    print()
    print("=" * 100)
    print("BP3  ⭐⭐ THE ACCEPTANCE RE-READ — closure against a requirement measured AT THE CELL")
    print("   required = pedal drive-tilt - model(OFF) drive-tilt, BOTH at this cell, so the")
    print("   clean tap both sides carry is common-mode and drops out of the difference.")
    print("   ⚠ It does NOT drop out of the two operands, which is why they are printed.")
    print()
    print(f"   {'cell':26s}{'cf':>8s}{'PEDAL':>10s}{'model OFF':>11s}{'required':>11s}"
          f"{'delivered':>12s}{'closure':>10s}")
    rows = {}
    for lab, _f, _L, _B in CELLS:
        p = BA.drive_tilt(ped[lab], vertex)
        m = BA.drive_tilt(mod_off[lab], vertex)
        req = p - m
        got = deliv[lab]["delivered"]
        clo = got / req if abs(req) > 1e-6 else float("nan")
        rows[lab] = {"pedal": p, "model_off": m, "required": req, "delivered": got,
                     "closure": clo, "cf": deliv[lab]["cf"]}
        print(f"   {lab:26s}{deliv[lab]['cf']:8.4f}{p:+10.4f}{m:+11.4f}{req:+11.4f}"
              f"{got:+12.4f}{clo:9.2f}x")

    c_corner, c_play = rows[CORNER]["closure"], rows[PLAY]["closure"]
    print(f"\n   ⭐ CLOSURE at BC's own cell {c_corner:.2f}x   at the PLAY cell {c_play:.2f}x")
    print("   ⚠ BC's published headline was `delivers 0.99x the requirement at all 5 conditions`,")
    print("     read on a DIFFERENT BUILD and against an IMPORTED bleed-free requirement — so the")
    print("     corner column here is the comparand, not BC's number itself.")

    # Computed verdict — the DIRECTION is derived, never narrated (s184).
    if not (np.isfinite(c_corner) and np.isfinite(c_play)):
        note("BP3", "closure is not finite at the corner or the play cell — the requirement is at "
                    "its own floor there and no ratio may be quoted.")
    else:
        ratio = c_play / c_corner if abs(c_corner) > 1e-12 else float("nan")
        word = ("UNDER-delivers" if ratio < 1.0 else "OVER-delivers") if abs(ratio - 1.0) > 0.10 \
            else "delivers the SAME fraction"
        print(f"   ⇒ relative to its own bleed-free acceptance the stage {word} at the play "
              f"setting ({ratio:.2f}x)")
        rows["_play_re_corner"] = ratio
    out["bp3"] = rows
    return rows


def bp3b(rows, deliv, out):
    """⚠ THE CONFOUND, SIZED — model and pedal are compared at the same KNOB, not the same MIX.

    A3 (GATE O) measures the model's OD path ~4.4 dB quiet against its OWN clean path, so at a given
    (LEVEL, BLEND) the MODEL sits at a HIGHER effective clean fraction than the pedal does.  BP3
    differences two sides at equal knob, so part of `required` is that mix-position difference and
    not a tilt difference at all.  This sub-gate does not remove it — it SIZES it, on the model's
    own measured cf -> tilt locus, and asks which way it points."""
    print()
    print("-" * 100)
    print("BP3b ⚠ THE A3 CONFOUND — same KNOB is not same MIX, so how far could cf alone explain it?")
    lad = sorted(out["bp2"]["ladder"], key=lambda l: deliv[l]["cf"])
    cf = [deliv[l]["cf"] for l in lad]
    off = [rows[l]["model_off"] for l in lad]
    print("      cf        " + "".join(f"{c:9.3f}" for c in cf))
    print("      model OFF " + "".join(f"{o:+9.3f}" for o in off))
    here = deliv[PLAY]["cf"]
    print()
    print("   THE ARGUMENT, in one step.  `cf` above is a COEFFICIENT clean fraction — a property")
    print("   of the pot network, the same on both sides.  A3 says the model's OD branch is ~4.4 dB")
    print("   quiet against its OWN clean tap, so at equal coefficient-cf the MODEL's output holds")
    print("   MORE clean ENERGY than the pedal's.  ⇒ the pedal at cf = c is comparable to the model")
    print("   at some c' < c, and the confound's direction is then just the SIGN of the model's own")
    print("   locus slope d(tilt)/d(cf) at the cell.")
    # Central difference on the measured locus at the play cell — no fit, no model of the mix.
    i = min(range(len(cf)), key=lambda k: abs(cf[k] - here))
    lo, hi = max(0, i - 1), min(len(cf) - 1, i + 1)
    slope = (off[hi] - off[lo]) / (cf[hi] - cf[lo]) if cf[hi] != cf[lo] else float("nan")
    print(f"\n   locus slope at cf {here:.3f} (central difference over cf {cf[lo]:.3f}..{cf[hi]:.3f}):"
          f"  {slope:+.3f} dB/oct per unit cf")
    if not np.isfinite(slope) or abs(slope) < 1e-9:
        print("   ⇒ the locus is flat here — the confound moves `required` in neither direction.")
        verdict = "flat"
    elif slope > 0:
        print("   ⇒ tilt becomes LESS negative as cf rises, so at the pedal's LOWER effective cf the")
        print("     model would read MORE negative still.  ⭐ The confound therefore UNDERSTATES")
        print("     `required`: correcting for A3 makes the model's excess LARGER, not smaller.")
        verdict = "understates"
    else:
        print("   ⇒ tilt becomes MORE negative as cf rises, so at the pedal's LOWER effective cf the")
        print("     model would read LESS negative.  ⚠ The confound INFLATES `required` at this")
        print("     cell and its SIZE is not safe.")
        verdict = "inflates"
    print("   ⚠⚠ PREMISE, printed every run: this uses the MODEL's own cf -> tilt locus to reason")
    print("     about where the pedal sits on it.  The pedal's locus is not the model's, so this")
    print("     bounds the confound's DIRECTION and never its size.  ⛔ It is also strictly local:")
    print("     the locus is NON-MONOTONE (it turns over near cf 0.24), so the sign is read at the")
    print("     cell and must not be extrapolated to the corner.")
    out["bp3b"] = {"cf": cf, "model_off": off, "cell_cf": here, "locus_slope": slope,
                   "verdict": verdict}


# ------------------------------------------------------------------------------------------------
# BP4 — the peak walk at the mix, both sides, matched membership
# ------------------------------------------------------------------------------------------------
def bp4(mod_off, mod_on, ped, out):
    print()
    print("=" * 100)
    print("BP4  THE PEAK WALK AT THE MIX — GATE BC's gate-2 consequence, both sides")
    print("   ⚠⚠ s183's BL3b established that the composite walk is dragged by the MIX itself (the")
    print("     clean tap does not roll off where the OD does, so it takes over the top of the band")
    print("     as the OD compresses).  So the ON-vs-OFF DIFFERENCE is the stage's contribution;")
    print("     the walk itself is not.  Both are printed, and the PEDAL's own walk with them.")
    print()
    _nm, kind, win, _l = W.FEAT_BY_NAME["treble_peak"]

    def read(per):
        rs = [W.locate(per[sw], win, kind) for sw in RUNGS]
        fs = [r["f0"] for r in rs]
        return (fs, 100.0 * (fs[-1] / fs[0] - 1.0),
                min(r["prom"] for r in rs), any(r["edge"] for r in rs))

    arms = ("off", "on", "ped")
    rows = {}
    for lab, _f, _L, _B in CELLS:
        rows[lab] = {t: read(p) for t, p in
                     (("off", mod_off[lab]), ("on", mod_on[lab]), ("ped", ped[lab]))}

    # ⭐⭐ THE PROMINENCE BAR IS AN AXIS HERE, NOT A DECISION (s137).  Its own distribution decides
    # nothing: the feature WASHES OUT with drive on BOTH sides, so the hottest rung — the one the
    # walk is defined by — is exactly where it dies.
    print(f"   {'cell':26s}" + "".join(f"{'min prom ' + t:>14s}" for t in arms))
    for lab, _f, _L, _B in CELLS:
        print(f"   {lab:26s}" + "".join(f"{rows[lab][t][2]:14.2f}" for t in arms))
    bars = (0.0, 0.5, W.MIN_PROM_DB)
    surv = {}
    for b in bars:
        surv[b] = [lab for lab, _f, _L, _B in CELLS
                   if all(rows[lab][t][2] >= b and not rows[lab][t][3] for t in arms)]
    print(f"\n   cells readable on ALL THREE arms, by prominence bar:")
    for b in bars:
        tag = "   <- GATE W's own bar" if b == W.MIN_PROM_DB else ("   <- no bar: GATE BC4's own "
                                                                  "convention" if b == 0.0 else "")
        print(f"      bar {b:.1f} dB : {len(surv[b]):2d} of {len(CELLS)}{tag}")
    if len(surv[W.MIN_PROM_DB]) == 0 and len(surv[0.0]) > 0:
        print("   ⛔⛔ AT GATE W's OWN BAR NOTHING RESOLVES, AND THAT IS A FINDING ABOUT GATE BC:")
        print("     BC4 reads `locate(...)['f0']` with NO validity check, so its published walk is")
        print("     read from rungs whose prominence GATE W would refuse.  The positions are")
        print("     interior and well inside their window, so they are not nonsense — but a walk")
        print("     built on them is a claim about a feature that is washing out, on both sides.")
    if not surv[0.0]:
        note("BP4", "no cell reads `treble_peak` interior on all three arms at ANY bar — the walk "
                    "cannot be read at the mix at all.")
        out["bp4"] = {"rows": {}, "survivors": {str(b): surv[b] for b in bars}}
        return

    print(f"\n   walks at bar 0.0 (BC4's convention), {len(surv[0.0])} cells:")
    print(f"   {'cell':26s}{'OFF':>9s}{'ON':>9s}{'stage':>9s}{'PEDAL':>9s}{'ON-PEDAL':>11s}")
    over = []
    for lab, _f, _L, _B in CELLS:
        if lab not in surv[0.0]:
            continue
        o, n, p = rows[lab]["off"][1], rows[lab]["on"][1], rows[lab]["ped"][1]
        if n < p:
            over.append(lab)
        print(f"   {lab:26s}{o:+8.2f}%{n:+8.2f}%{n - o:+8.2f}%{p:+8.2f}%{n - p:+10.2f}%")
    print(f"\n   ⇒ {len(over)} of {len(surv[0.0])} cells OVERSHOOT the pedal's own walk at that cell")
    if over:
        print(f"     {', '.join(sorted(over))}")
    print("   ⚠ `stage` (ON - OFF) is the stage's own contribution; the walk itself is dragged by")
    print("     the MIX as well (s183's BL3b), so only that column is attributable to the stage.")
    out["bp4"] = {"rows": {l: {t: [v[1], v[2], bool(v[3])] for t, v in r.items()}
                           for l, r in rows.items()},
                  "survivors": {str(b): surv[b] for b in bars}, "overshoot": sorted(over)}


# ------------------------------------------------------------------------------------------------
# BP5 — verdict
# ------------------------------------------------------------------------------------------------
def bp5(out):
    print()
    print("=" * 100)
    print("BP5  VERDICT")
    d = out["bp2"]["rows"]
    c = out["bp3"]
    play_frac = abs(d[PLAY]["delivered"] / d[CORNER]["delivered"]) \
        if abs(d[CORNER]["delivered"]) > 1e-12 else float("nan")
    print(f"   delivery at the PLAY cell        {play_frac * 100:6.1f} % of the corner's")
    print(f"   |delivery| monotone in cf        {out['bp2']['monotone']}")
    print(f"   closure  corner {c[CORNER]['closure']:+.2f}x   play {c[PLAY]['closure']:+.2f}x")
    print(f"   `required` sign, mixed cells     {out['bp2b']['mixed_positive']} of "
          f"{out['bp2b']['mixed_total']} POSITIVE (model already over-tilted)")
    print(f"   A3 confound points               {out['bp3b']['verdict']}")
    print(f"   scope controls bit-identical     {out['bp1']['scope_worst'] == 0.0}")
    print(f"   walk cells at GATE W's own bar   {len(out['bp4']['survivors'][str(W.MIN_PROM_DB)])} "
          f"of {len(CELLS)}")
    print()
    print("   ⛔ NOTHING HERE IS A SHIP DECISION.  The stage is unchanged; this is a re-read of an")
    print("     acceptance number at settings its acceptance never covered.")
    print()
    print(f"   BP5-MEMBERSHIP cells=[{','.join(sorted(f for _l, f, _L, _B in CELLS))}]")
    print(f"   BP5-VERDICT play_delivery_frac={play_frac:.4f} "
          f"closure_corner={c[CORNER]['closure']:.4f} closure_play={c[PLAY]['closure']:.4f} "
          f"monotone={out['bp2']['monotone']} scope_ok={out['bp1']['scope_worst'] == 0.0}")
    out["bp5"] = {"play_delivery_frac": play_frac,
                  "closure_corner": c[CORNER]["closure"], "closure_play": c[PLAY]["closure"]}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", default=None)
    ap.add_argument("--jobs", type=int, default=JOBS)
    args = ap.parse_args()
    os.makedirs(PRIV_DIR, exist_ok=True)
    out = {}
    cells = bp0(out)

    before = BA.fingerprint(W.REN_DIR)
    W._load_orig()          # prime the module globals BEFORE threading (s133's race)
    jobs = [(f, on) for _l, f, _L, _B in CELLS for on in (False, True)] + \
           [(f, on) for _l, f in SCOPE for on in (False, True)]
    print(f"\n   rendering {len(jobs)} conditions (tilt ON and OFF) on {args.jobs} jobs ...")
    with ThreadPoolExecutor(max_workers=args.jobs) as ex:
        list(ex.map(do_render, jobs))
    print("   done")

    mod_off = {lab: model_curves(f, False) for lab, f, _L, _B in CELLS}
    mod_on = {lab: model_curves(f, True) for lab, f, _L, _B in CELLS}
    ped = {lab: pedal_curves(f) for lab, f, _L, _B in CELLS}

    # ⭐ The read frequency is MEASURED, not transcribed: the corner's own tilt-OFF treble peak,
    # located by GATE W's own locator.  One frequency for every cell, because the quantity being
    # compared across cells is the SAME stage's shelf — which does not move with the mix.
    _nm, kind, win, _l = W.FEAT_BY_NAME["treble_peak"]
    r = W.locate(mod_off[CORNER][RUNGS[0]], win, kind)
    if not valid(r):
        die("BP0", f"the corner's tilt-OFF treble peak is not a valid reading "
                   f"(edge={r['edge']}, prom={r['prom']:.2f}) — the read frequency would be a "
                   f"window bound, not a measurement.")
    vertex = r["f0"]
    print(f"   read frequency (MEASURED): the corner's tilt-OFF treble peak = {vertex:.1f} Hz "
          f"(prominence {r['prom']:.2f} dB)")
    out["vertex_hz"] = vertex

    bp1(mod_off, mod_on, vertex, out)
    deliv = bp2(mod_off, mod_on, cells, vertex, out)
    bp2b(mod_off, mod_on, ped, out)
    clo = bp3(mod_off, ped, deliv, vertex, out)
    bp3b(clo, deliv, out)
    bp4(mod_off, mod_on, ped, out)
    bp5(out)

    if BA.fingerprint(W.REN_DIR) != before:
        die("BP0", "GATE W's read-only render cache CHANGED during this run.")
    print(f"\n   GATE W cache integrity: {len(before)} files unchanged")
    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"   wrote {args.json}")
    print("=" * 100)
    sys.exit(1 if FAILED else 0)


if __name__ == "__main__":
    main()
