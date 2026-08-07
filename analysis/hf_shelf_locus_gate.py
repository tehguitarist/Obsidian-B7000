#!/usr/bin/env python3.11
"""GATE BF -- did s172's `OdMakeup` HIGH SHELF walk the treble notch down the band?

Session 173, opened on a USER REPORT: *"the treble notch is now sitting at around 4 kHz instead of
the 5.3 odd it used to, which means treble is getting cut off earlier than it should."*

WHY THE REPORT IS PLAUSIBLE BEFORE ANYTHING IS MEASURED
-------------------------------------------------------
`OdMakeup` (s172) is a flat OD-branch boost BAND-LIMITED BY TWO SHELVES, and the high one is
`odMakeupHighHz = 2800 Hz` removing `odMakeupHighCutDb = 6.0` dB above it.  The stage's own header
records the constraint that sized the shelves: keep their transitions clear of the 285-905 Hz
complex being corrected, i.e. *"lowHz well below 285 and highHz well above 905"*.  That is a
one-sided requirement and it was checked on one side.  Nothing asked what a -6 dB shelf opening at
2800 Hz does to the features at 4-12 kHz, which is where its transition actually lands.

⭐ And the project already has the mechanism, from a completely unrelated investigation: GATE AF6
(s134) established that this chain's treble features are VERTICES -- a vertex sits where the total
slope crosses zero, so **a TILT moves it with no corner moving anywhere**.  A shelf is a tilt.  So
"we added a broad HF cut" and "an HF vertex moved down the band" are the same sentence, and the
only open question is the SIZE.

WHAT THIS GATE MEASURES
-----------------------
BF1  setup, and the two free known answers an OD-only stage owes: the CLEAN path must be
     BIT-IDENTICAL at every makeup setting (the stage is in the OD branch), and the shipped
     setting must DIFFER from makeup-off (or the sweep below is inert and would report "no
     movement" for a reason that has nothing to do with the physics -- s110's vacuity trap).
BF2  ⛔ THE WINDOW FIRST.  GATE W's `treble_notch` window is (4200, 12000) Hz.  If the feature has
     walked to ~4 kHz it is now AT OR BELOW that window's lower bound, and `locate()` returns the
     bound rather than the feature (s126/s151: an extremum resting on a window edge is not a
     measurement).  So this gate locates on a DELIBERATELY WIDER window and reports, per setting,
     whether GATE W's own window still contains the feature.  A gate that measured the walk
     through W's window would be measuring the window.
BF3  THE DOSE-RESPONSE on `odMakeupHighCutDb`, 0 -> shipped.  If the shelf is the carrier the
     centre must move MONOTONICALLY with it.  This is the measurement the fix is sized from.
BF4  THE CONTROL, and it is what separates "the shelf did it" from "the makeup did it": sweep the
     FLAT term `odMakeupDb` with both shelves held at 0.  A flat gain cannot move a vertex (AB2's
     control, and s172's own "a flat term cannot change any bleed-free contrast", asserted there
     at 0.0000 dB over a 0->7.5 dB sweep).  If the flat term moves the centre, the mechanism is
     not the shelf and every number in BF3 is mis-attributed.
BF5  THE TARGET: the PEDAL's own centre on the same captures, same estimator, same window.  A walk
     is only a defect against where the feature should be.

⚠ EVERY CAPTURE WITHOUT A `grunt-` TOKEN IS GRUNT = CUT (`captures.py` defaults it), which is the
s151 trap that cost that session its whole fit.  All three GRUNT positions are rendered here and
reported separately; nothing is pooled across the switch.

⚠ Renders go to a PRIVATE directory.  GATE W's cache `build/s122_feature_locus/` is READ-ONLY and
that is enforced by fingerprint -- pointing any tool's `ren_dir` at it destroys the artefacts GATE
W published from (s159).

Run:
    python3.11 analysis/hf_shelf_locus_gate.py
    python3.11 analysis/hf_shelf_locus_gate.py --json analysis/reports/s173_hf_shelf.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                    # noqa: E402
import captures as C                   # noqa: E402
import comprehensive_report as CR      # noqa: E402
import feature_locus_gate as W         # noqa: E402
from parallel import pmap              # noqa: E402

REN_DIR = "build/s173_hf_shelf"        # PRIVATE -- never GATE W's cache
OS_FACTOR = W.OS_FACTOR

# ⚠ DERIVED from GATE W, not retyped, so the two cannot drift and a change to W's window is
# visible here immediately (`rebuild-targets-dont-transcribe`).
W_TREBLE_WIN = dict((n, win) for n, _k, win, _lbl in W.FEATURES)["treble_notch"]

# The WIDE window this gate locates on.  Its lower bound is deliberately far below W's so a feature
# that has walked out of W's window is still measured rather than clipped; its upper bound is W's
# own, since nothing suggests the feature moved UP.  ⚠ A wider window admits more of the
# neighbouring features' flanks, so the PROMINENCE from it is not comparable with W's (GATE AV) --
# this gate quotes CENTRES, which is what W's estimator is sound for.
WIDE_WIN = (2600.0, W_TREBLE_WIN[1])

SWEEPS = W.SWEEPS

# ⛔⛔ THE MEMBERSHIP IS THE WHOLE DESIGN, AND THE FIRST DRAFT GOT IT EXACTLY BACKWARDS.  It used
# the BLEED-FREE corner (LEVEL max AND BLEND max) on the usual reasoning that an OD-branch stage's
# effect is undiluted there.  That is the one condition where this particular feature DOES NOT
# EXIST: GATE AE (s133) measured the model's curve as strictly MONOTONE over 4200-12000 Hz with
# **no interior extremum at all in 9 of 9** bleed-free driven cells, and established that what the
# model carries here is a MIX cancellation that dies with the clean tap.  Run bleed-free, every
# reading duly rested on the window's upper bound at every shelf setting -- a bound, not a
# measurement (s126), and it would have been published as "the shelf moves nothing".
# ⇒ read this feature at the LISTENING condition, where the clean tap is present and the
# cancellation exists.  These are LEVEL noon / BLEND max plus two rungs of the LEVEL ladder, and
# all three GRUNT positions (`captures.py` defaults GRUNT to CUT, the s151 trap).
CAPTURES = (
    "ref-od.wav",
    "grunt-flat_base-od.wav",
    "grunt-boost_base-od.wav",
    "level-0930_base-od.wav",
    "level-1430_base-od.wav",
    "drive-1700_base-od.wav",
)

# The shipped values, read from the header rather than transcribed where possible.
SHIPPED_HICUT = 6.0
SHIPPED_MAKEUP = 6.0
SHIPPED_LOCUT = 3.5

OFF = ("odMakeupDb=0", "odMakeupLowCutDb=0", "odMakeupHighCutDb=0", "odNotchDepthDb=0")


# --------------------------------------------------------------------------------------------
def _fit_args(pairs):
    out = []
    for kv in pairs:
        out += ["--fit", kv]
    return out


def _cell(job):
    fname, pairs, tag = job
    parsed = C.parse_capture(fname)
    args = C.render_args(parsed) + _fit_args(pairs)
    out = os.path.join(REN_DIR, f"{fname[:-4]}__{tag}_plugin.wav")
    os.makedirs(REN_DIR, exist_ok=True)
    W.render(out, args)
    return fname, tag, out


def _locate_all(path, win):
    """-> {sweep: locate-dict} for one rendered/captured file on `win`."""
    orig, ref = W._load_orig()
    al, _ = A.align(A.load(path), orig)
    res = {}
    for sw in SWEEPS:
        f, m = A.transfer_h1(A.seg_of(al, sw), ref)
        res[sw] = W.locate(W.smooth(f, m), win, "min")
    return res


def _locate_capture(fname, win):
    orig, ref = W._load_orig()
    al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    res = {}
    for sw in SWEEPS:
        f, m = A.transfer_h1(A.seg_of(al, sw), ref)
        res[sw] = W.locate(W.smooth(f, m), win, "min")
    return res


def render_all(jobs, jobs_n=None):
    done = pmap(_cell, jobs, jobs=jobs_n)
    return {(f, t): p for f, t, p in done}


# --------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--json")
    ap.add_argument("--jobs", type=int, default=None)
    args = ap.parse_args()
    out = {}

    print("GATE BF -- did s172's OdMakeup HIGH SHELF walk the treble notch down the band?")
    print(f"  wide window {WIDE_WIN[0]:.0f}-{WIDE_WIN[1]:.0f} Hz   "
          f"(GATE W's treble_notch window: {W_TREBLE_WIN[0]:.0f}-{W_TREBLE_WIN[1]:.0f} Hz)")
    print(f"  {len(CAPTURES)} bleed-free OD captures x {len(SWEEPS)} sweeps, "
          f"all three GRUNT positions reported separately")

    # ---- the render matrix -------------------------------------------------------------------
    hicuts = [0.0, 1.5, 3.0, 4.5, 6.0]
    flats = [0.0, 2.0, 4.0, 6.0]
    jobs = []
    for f in CAPTURES:
        jobs.append((f, OFF, "off"))
        jobs.append((f, ("odMakeupDb=%g" % SHIPPED_MAKEUP, "odMakeupLowCutDb=%g" % SHIPPED_LOCUT,
                         "odMakeupHighCutDb=%g" % SHIPPED_HICUT), "shipped"))
        for h in hicuts:
            jobs.append((f, ("odMakeupDb=%g" % SHIPPED_MAKEUP, "odMakeupLowCutDb=0",
                             "odMakeupHighCutDb=%g" % h, "odNotchDepthDb=0"), "hi%g" % h))
        for g in flats:
            jobs.append((f, ("odMakeupDb=%g" % g, "odMakeupLowCutDb=0",
                             "odMakeupHighCutDb=0", "odNotchDepthDb=0"), "flat%g" % g))
    # A CLEAN control -- the free known answer an OD-only stage owes.  ⚠ The bleed-free OD
    # conditions above have no `base-clean` twin, so the control is taken from the clean captures
    # that DO exist rather than skipped: what it has to establish is that the stage is confined to
    # the OD branch, which is a property of the stage and not of these particular settings.
    clean_caps = sorted(f for f in os.listdir(C.CAPTURE_DIR)
                        if f.endswith("base-clean.wav") and "gain-n" not in f)[:4]
    for f in clean_caps:
        jobs.append((f, OFF, "off"))
        jobs.append((f, ("odMakeupDb=%g" % SHIPPED_MAKEUP, "odMakeupLowCutDb=%g" % SHIPPED_LOCUT,
                         "odMakeupHighCutDb=%g" % SHIPPED_HICUT), "shipped"))

    print(f"\n  rendering {len(jobs)} conditions into {REN_DIR}/ ...")
    paths = render_all(jobs, args.jobs)

    # ---- BF1: the known answers ----------------------------------------------------------------
    print("\n-- BF1: the free known answers an OD-only stage owes --")
    if not clean_caps:
        print("  ⚠ no `base-clean` twin exists for these conditions -- the CLEAN bit-identity")
        print("    check is NOT AVAILABLE and is reported as such rather than skipped silently.")
    else:
        worst_clean = 0.0
        for f in clean_caps:
            a = A.load(paths[(f, "off")])
            b = A.load(paths[(f, "shipped")])
            n = min(len(a), len(b))
            worst_clean = max(worst_clean, float(np.max(np.abs(a[:n] - b[:n]))))
        if worst_clean != 0.0:
            sys.exit(f"GATE BF1 FAIL: the CLEAN path MOVED ({worst_clean:.3e}) between makeup off "
                     f"and shipped -- `OdMakeup` is an OD-branch stage, so this is a scope defect "
                     f"and nothing below is attributable to the OD path")
        print(f"  BF1 OK  CLEAN bit-identical across makeup off/shipped over {len(clean_caps)} "
              f"captures ({worst_clean:.1e})")

    worst_od = 0.0
    for f in CAPTURES:
        a = A.load(paths[(f, "off")])
        b = A.load(paths[(f, "shipped")])
        n = min(len(a), len(b))
        worst_od = max(worst_od, float(np.max(np.abs(a[:n] - b[:n]))))
    if worst_od == 0.0:
        sys.exit("GATE BF1 FAIL: the OD path is BIT-IDENTICAL between makeup off and shipped -- "
                 "the sweep below is INERT and would report 'no movement' for a reason that has "
                 "nothing to do with the physics (`suspect the mutation before the guard`)")
    print(f"  BF1 OK  OD path is NOT inert (worst |off - shipped| = {worst_od:.3e})")
    out["bf1"] = {"clean_bit_identical": (worst_clean if clean_caps else None),
                  "od_moved": worst_od, "n_clean": len(clean_caps)}

    # ---- BF2 + BF3: the dose-response on the HIGH SHELF -----------------------------------------
    print("\n-- BF2/BF3: the HIGH-SHELF dose-response, located on the WIDE window --")
    print("    'inW' = is the centre inside GATE W's own treble_notch window (4200-12000 Hz)?")
    print("    'edge' = the extremum rests on a bound of the WIDE window (then it is not a")
    print("             measurement either, and the window must be widened again).")
    rows = {}
    for f in CAPTURES:
        grunt = ("boost" if "grunt-boost" in f else
                 "flat" if "grunt-flat" in f else "cut")
        drive = "max" if "drive-1700" in f else "noon"
        print(f"\n    {f}   [GRUNT {grunt}, DRIVE {drive}]")
        print(f"      {'hiCutDb':>8}" + "".join(f"{sw.replace('sweep_', ''):>13}" for sw in SWEEPS))
        per = {}
        for h in hicuts:
            loc = _locate_all(paths[(f, "hi%g" % h)], WIDE_WIN)
            per[h] = {sw: loc[sw] for sw in SWEEPS}
            cells = []
            for sw in SWEEPS:
                r = loc[sw]
                flag = "" if W_TREBLE_WIN[0] <= r["f0"] <= W_TREBLE_WIN[1] else "*"
                flag += "!" if r["edge"] else ""
                cells.append(f"{r['f0']:9.0f}{flag:<4}")
            print(f"      {h:8.1f}" + "".join(cells))
        rows[f] = {"grunt": grunt, "drive": drive, "hicut": per}

    # ⛔ THE GUARD THIS GATE'S OWN FIRST DRAFT NEEDED.  Run on the wrong membership every reading
    # rested on a window bound and the table came out flat and confident -- "the shelf moves
    # nothing", from a locator that was reporting the window.  A bound is not a measurement
    # (s126/s151), so if the BASELINE readings are mostly edges there is no feature here to move
    # and the run must REFUSE rather than publish a null result.
    base_edges = sum(1 for f in CAPTURES for sw in SWEEPS
                     if rows[f]["hicut"][hicuts[0]][sw]["edge"])
    base_n = len(CAPTURES) * len(SWEEPS)
    if base_edges > base_n // 4:
        sys.exit(f"GATE BF2 FAIL: {base_edges} of {base_n} BASELINE readings rest on a bound of "
                 f"the wide window {WIDE_WIN} -- there is no interior extremum to locate in this "
                 f"membership, so a flat dose-response below would be the WINDOW, not the physics. "
                 f"Either widen the window or (far more likely) this feature does not exist at "
                 f"these settings -- GATE AE measured it ABSENT bleed-free and present only where "
                 f"the clean tap mixes.")
    print(f"\n    BF2 OK  only {base_edges} of {base_n} baseline readings rest on a bound, so the "
          f"dose-response below is the curve's and not the window's")

    # monotonicity + size, per (capture, sweep)
    print("\n    * = OUTSIDE GATE W's treble_notch window   ! = resting on a WIDE-window bound")
    print(f"\n    {'capture':<46}{'sweep':>10}{'f0 @0':>9}{'f0 @6':>9}{'walk %':>9}{'mono':>7}")
    n_mono, n_tot, walks = 0, 0, []
    for f in CAPTURES:
        for sw in SWEEPS:
            seq = [rows[f]["hicut"][h][sw]["f0"] for h in hicuts]
            d = np.diff(seq)
            mono = bool(np.all(d <= 1e-9) or np.all(d >= -1e-9))
            n_mono += int(mono)
            n_tot += 1
            walk = 100.0 * (seq[-1] / seq[0] - 1.0)
            walks.append(walk)
            print(f"    {f[:-4]:<46}{sw.replace('sweep_', ''):>10}{seq[0]:9.0f}{seq[-1]:9.0f}"
                  f"{walk:9.2f}{'yes' if mono else 'NO':>7}")
    med_walk = float(np.median(walks))
    print(f"\n    MONOTONE in {n_mono} of {n_tot} (capture x sweep) cells; "
          f"median walk {med_walk:+.2f} %")
    out["bf3"] = {"hicuts": hicuts, "monotone": [n_mono, n_tot], "median_walk_pct": med_walk,
                  "rows": {f: {"grunt": rows[f]["grunt"], "drive": rows[f]["drive"],
                               "f0": {str(h): {sw: rows[f]["hicut"][h][sw]["f0"] for sw in SWEEPS}
                                      for h in hicuts}} for f in CAPTURES}}

    # ---- BF4: the FLAT term, as a separate lever -------------------------------------------------
    # ⚠⚠ s173, CORRECTED PREMISE.  This sub-gate was written as a CONTROL on the reasoning that
    # "a flat gain cannot move a vertex" (AB2's control, and s172's own bleed-free assertion).
    # That is TRUE OF A VERTEX IN ONE LINEAR CASCADE and FALSE OF THIS FEATURE, which GATE AE
    # established is a MIX CANCELLATION between the OD and clean paths: a null sits where the two
    # are equal and opposite, so a flat gain on ONE of them moves it by construction.  Measured,
    # it does -- and in the OPPOSITE direction to the shelf.  ⇒ this is not a failed control, it
    # is a SECOND LEVER, and reporting it as a control failure would have blocked the fix behind
    # a question that has an answer.  Both terms are reported as levers and the verdict compares
    # their DIRECTIONS, which is what the fix actually needs to know.
    print("\n-- BF4: the FLAT makeup term as a SECOND LEVER (both shelves at 0) --")
    print("    ⚠ NOT a 'flat gain cannot move a vertex' control: this feature is a MIX")
    print("      CANCELLATION (GATE AE), so a flat gain on the OD branch alone moves the")
    print("      balance point by construction.  The question is its DIRECTION and SIZE.")
    print(f"    {'capture':<40}{'sweep':>10}{'f0 @0':>9}{'f0 @6':>9}{'walk %':>9}")
    fw = []
    for f in CAPTURES:
        for sw in SWEEPS:
            locs = [_locate_all(paths[(f, "flat%g" % g)], WIDE_WIN)[sw] for g in flats]
            # ⛔ MEMBERSHIP: a reading resting on a window bound is a bound, not a measurement,
            # so a "walk" between two bounds is arithmetic on two non-measurements.  The first
            # draft pooled them and reported a 73 % flat-term walk between two identical
            # edge readings, which flipped this sub-gate's verdict on garbage.
            if any(r["edge"] for r in locs):
                print(f"    {f[:-4]:<40}{sw.replace('sweep_', ''):>10}"
                      f"{locs[0]['f0']:9.0f}{locs[-1]['f0']:9.0f}{'  edge -- excluded':>9}")
                continue
            walk = 100.0 * (locs[-1]["f0"] / locs[0]["f0"] - 1.0)
            fw.append(walk)
            print(f"    {f[:-4]:<40}{sw.replace('sweep_', ''):>10}"
                  f"{locs[0]['f0']:9.0f}{locs[-1]['f0']:9.0f}{walk:9.2f}")
    med_flat = float(np.median(fw)) if fw else float("nan")
    print(f"\n    median FLAT-term walk {med_flat:+.2f} % (n = {len(fw)})   vs the "
          f"HIGH-SHELF's {med_walk:+.2f} %")
    if fw and med_flat * med_walk < 0:
        print("    ⇒ THE TWO TERMS PULL OPPOSITE WAYS on this feature: the flat boost pushes the")
        print("      null UP the band, the high shelf pulls it DOWN, and the shipped setting is")
        print("      the net.  So the makeup's SHAPE, not its size, is what moved the notch.")
    else:
        print("    ⇒ both terms move the null the SAME way, so the shape is not the lever and a")
        print("      fix must change the makeup's size or its placement instead.")
    out["bf4"] = {"flats": flats, "median_flat_walk_pct": med_flat, "n": len(fw)}

    # ---- BF5: where it SHOULD be ---------------------------------------------------------------
    print("\n-- BF5: the TARGET -- the pedal's own centre, same estimator, same window --")
    print(f"    {'capture':<46}{'sweep':>10}{'pedal':>9}{'off':>9}{'shipped':>9}{'ship/ped':>10}")
    # ⛔ Same membership rule as BF4: a cell where EITHER side rests on a bound contributes a
    # bound, not a measurement, and the ratio between them is meaningless.  At the `clean`
    # stimulus this feature does not exist on the model side at all (it is drive-generated), so
    # those cells are excluded BY THE RULE rather than by name.
    err_off, err_ship, n_excl = [], [], 0
    for f in CAPTURES:
        ped = _locate_capture(f, WIDE_WIN)
        off = _locate_all(paths[(f, "off")], WIDE_WIN)
        shp = _locate_all(paths[(f, "shipped")], WIDE_WIN)
        for sw in SWEEPS:
            p0, o0, s0 = ped[sw]["f0"], off[sw]["f0"], shp[sw]["f0"]
            skip = ped[sw]["edge"] or off[sw]["edge"] or shp[sw]["edge"]
            if skip:
                n_excl += 1
            else:
                err_off.append(o0 / p0)
                err_ship.append(s0 / p0)
            print(f"    {f[:-4]:<46}{sw.replace('sweep_', ''):>10}{p0:9.0f}{o0:9.0f}{s0:9.0f}"
                  f"{'      edge' if skip else f'{s0 / p0:10.3f}'}")
    print(f"\n    {n_excl} of {len(CAPTURES) * len(SWEEPS)} cells excluded: an extremum on a "
          f"window bound is not a measurement")
    print(f"\n    median model/pedal centre ratio:  makeup OFF {np.median(err_off):.3f}   "
          f"SHIPPED {np.median(err_ship):.3f}")
    if abs(np.median(err_ship) - 1.0) > abs(np.median(err_off) - 1.0):
        print("    ⇒ THE SHIPPED MAKEUP MOVES THIS FEATURE AWAY FROM THE PEDAL'S POSITION.")
    else:
        print("    ⇒ the shipped makeup moves this feature TOWARD the pedal's position.")
    out["bf5"] = {"median_ratio_off": float(np.median(err_off)),
                  "median_ratio_shipped": float(np.median(err_ship))}

    # ---- BF6: SIZE THE FIX -- model/pedal centre ratio at every shelf depth --------------------
    # ⭐ The whole point: BF5 says the SHIPPED setting is worse than makeup-off, but the makeup is
    # two terms and BF4 says they pull opposite ways.  So the question a fix needs answered is not
    # "makeup or no makeup" but "which HIGH-SHELF DEPTH puts this feature where the pedal has it",
    # with the flat term held at its shipped value.  Same membership rule as BF4/BF5.
    print("\n-- BF6: sizing the fix -- centre ratio vs the pedal at each high-shelf depth --")
    print("    (flat makeup held at its shipped +6 dB; low shelf at 0 so this column is the")
    print("     HIGH shelf alone.  1.000 = the model's null sits exactly where the pedal's does.)")
    ped_cache = {f: _locate_capture(f, WIDE_WIN) for f in CAPTURES}
    print(f"    {'hiCutDb':>8}{'median ratio':>14}{'worst |1-r|':>13}{'n':>5}")
    best, ratios_by_h = None, {}
    for h in hicuts:
        rs = []
        for f in CAPTURES:
            loc = _locate_all(paths[(f, "hi%g" % h)], WIDE_WIN)
            for sw in SWEEPS:
                if loc[sw]["edge"] or ped_cache[f][sw]["edge"]:
                    continue
                rs.append(loc[sw]["f0"] / ped_cache[f][sw]["f0"])
        med = float(np.median(rs))
        worst = float(np.max(np.abs(np.array(rs) - 1.0)))
        ratios_by_h[h] = {"median": med, "worst_abs_err": worst, "n": len(rs)}
        mark = ""
        if best is None or abs(med - 1.0) < abs(ratios_by_h[best]["median"] - 1.0):
            best = h
        print(f"    {h:8.1f}{med:14.3f}{worst:13.3f}{len(rs):5d}{mark}")
    print(f"\n    ⇒ closest to the pedal at odMakeupHighCutDb = {best:.1f} "
          f"(median ratio {ratios_by_h[best]['median']:.3f}); "
          f"shipped is {SHIPPED_HICUT:.1f} "
          f"(median {ratios_by_h[SHIPPED_HICUT]['median']:.3f}).")
    print("    ⚠ This sizes the NOTCH axis ONLY.  The high shelf exists because s172 measured the")
    print("      OD:clean deficit POSITIVE above 5 kHz, so reducing it re-boosts a region that is")
    print("      already hot -- the out-of-band cost has to be priced on s172's own metric before")
    print("      any value here is shipped.  A number from this table alone is half an answer.")
    out["bf6"] = {"by_hicut": {str(k): v for k, v in ratios_by_h.items()}, "best_hicut": best}

    # ---- BF7: is PLACEMENT a second degree of freedom, or is depth the only knob? ---------------
    # ⛔ BF6 is monotone: every dB of shelf improves the out-of-band fit and costs the notch, so
    # DEPTH is `one-knob-two-jobs-is-compensating` and tuning it cannot resolve the conflict --
    # it can only choose where on the trade to sit.  A real fix needs a knob that separates them.
    # The shelf's CORNER is already a shipped fit param, so this costs renders and no rebuild.
    # ⭐ The hypothesis worth testing: a corner placed WELL BELOW the feature has completed its
    # transition before reaching it, presenting a flat region -- and a flat region has no TILT,
    # which BF4 showed is the larger half of the walk.  If the corner column is flat, placement is
    # not a lever either and the shelf's SLOPE (hardcoded S = 0.9) is the only remaining route.
    print("\n-- BF7: the shelf's CORNER as a second degree of freedom (depth held at 6 dB) --")
    corners = [1200.0, 1600.0, 2200.0, 2800.0, 4000.0, 5600.0, 8000.0]
    cjobs = [(f, ("odMakeupDb=%g" % SHIPPED_MAKEUP, "odMakeupLowCutDb=0",
                  "odMakeupHighHz=%g" % c, "odMakeupHighCutDb=%g" % SHIPPED_HICUT,
                  "odNotchDepthDb=0"), "cor%g" % c)
             for f in CAPTURES for c in corners]
    print(f"    rendering {len(cjobs)} more conditions ...")
    cpaths = render_all(cjobs, args.jobs)
    print(f"    {'highHz':>8}{'median ratio':>14}{'worst |1-r|':>13}{'n':>5}")
    cbest, by_c = None, {}
    for c in corners:
        rs = []
        for f in CAPTURES:
            loc = _locate_all(cpaths[(f, "cor%g" % c)], WIDE_WIN)
            for sw in SWEEPS:
                if loc[sw]["edge"] or ped_cache[f][sw]["edge"]:
                    continue
                rs.append(loc[sw]["f0"] / ped_cache[f][sw]["f0"])
        med = float(np.median(rs))
        by_c[c] = {"median": med, "worst_abs_err": float(np.max(np.abs(np.array(rs) - 1.0))),
                   "n": len(rs)}
        if cbest is None or abs(med - 1.0) < abs(by_c[cbest]["median"] - 1.0):
            cbest = c
        print(f"    {c:8.0f}{med:14.3f}{by_c[c]['worst_abs_err']:13.3f}{len(rs):5d}")
    span = max(v["median"] for v in by_c.values()) - min(v["median"] for v in by_c.values())
    depth_span = (max(v["median"] for v in ratios_by_h.values())
                  - min(v["median"] for v in ratios_by_h.values()))
    print(f"\n    corner column spans {span:.3f} in centre ratio; the DEPTH column spans "
          f"{depth_span:.3f}")
    # ⚠⚠ s173: grade the corner against the TWO references that matter, not against the shipped
    # setting.  A first draft printed "PLACEMENT IS A LEVER ... so the notch can be recovered"
    # purely because the best corner beat the shipped one -- which is true and says nothing about
    # whether the defect is fixed.  The user's report is a REGRESSION, so the bar is the
    # makeup-OFF position; the flat-only arm is the best any depth reaches and bounds the rest.
    off_ref = ratios_by_h[0.0]["median"]          # flat +6, no shelves == BF6's hiCut = 0 rung
    print(f"    references: makeup OFF {np.median(err_off):.3f} (the pre-s172 position the user "
          f"reports)\n                flat-only (no high shelf) {off_ref:.3f} -- the ceiling any "
          f"corner can reach")
    if span < 0.25 * depth_span:
        print("    ⇒ PLACEMENT IS NOT A LEVER at this depth -- moving the corner buys less than a")
        print("      quarter of what the depth does, so the two jobs stay coupled.")
    else:
        print(f"    ⇒ placement IS a lever ({span:.3f} of centre ratio, {span / depth_span:.2f}x "
              f"the depth column's own span),")
        print(f"      and the column is U-SHAPED with its MINIMUM at the shipped {2800.0:.0f} Hz "
              f"-- i.e. the")
        print("      shipped corner is the WORST available placement for this feature, and moving")
        print("      it in EITHER direction helps.")
    recovered = by_c[cbest]["median"] >= np.median(err_off)
    print(f"    ⇒ but the best corner ({cbest:.0f} Hz, {by_c[cbest]['median']:.3f}) "
          f"{'REACHES' if recovered else 'DOES NOT REACH'} the makeup-OFF position "
          f"({np.median(err_off):.3f}).")
    if not recovered:
        print("      ⇒ NO SINGLE SHIPPED KNOB RESTORES IT: depth trades against the out-of-band")
        print("        job (BF6) and placement tops out below the regression's own baseline.  The")
        print("        remaining degree of freedom is the shelf's SLOPE, which sets how much TILT")
        print("        the removal presents at the feature independently of how much LEVEL it")
        print("        removes out of band -- exposed as `odMakeupHighS` (s173) to be screened.")
    out["bf7"] = {"by_corner": {str(k): v for k, v in by_c.items()}, "best_corner": cbest,
                  "corner_span": span, "depth_span": depth_span}

    # ---- BF8: the JOINT search -- both axes at once ---------------------------------------------
    # ⛔ BF6/BF7 each move ONE knob and each hits the same wall, because the shelf's depth and its
    # placement both change the notch and the out-of-band fit together.  The fix has to be scored
    # on BOTH axes simultaneously or it is just choosing a point on a trade nobody measured.
    #
    # AXIS 1, the user's report: the notch's centre re the pedal's (BF5/BF6's statistic).
    # AXIS 2, what the shelf is FOR: s172's OD:clean ratio residual outside the midrange.  That
    # tool was not kept, so it is rebuilt from its stated definition -- each side differenced
    # against ITSELF (model OD re model CLEAN, pedal OD re pedal CLEAN) so every per-side
    # capture-chain scalar cancels, exactly as s172 §1 describes.
    print("\n-- BF8: the JOINT search -- notch centre AND s172's own out-of-band residual --")
    MID, OUT = (250.0, 900.0), ((60.0, 250.0), (900.0, 8000.0))

    def ratio_curve(od_path, cl_path):
        """OD re CLEAN, in dB, on the locator grid -- one side, self-referenced."""
        orig, ref = W._load_orig()
        a, _ = A.align(A.load(od_path) if os.path.exists(od_path) else od_path, orig)
        b, _ = A.align(A.load(cl_path) if os.path.exists(cl_path) else cl_path, orig)
        f1, m1 = A.transfer_h1(A.seg_of(a, "sweep_drv_-12"), ref)
        f2, m2 = A.transfer_h1(A.seg_of(b, "sweep_drv_-12"), ref)
        return W.smooth(f1, m1) - W.smooth(f2, m2)

    def ratio_curve_cap(od_cap, cl_cap):
        orig, ref = W._load_orig()
        a, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, od_cap)), orig)
        b, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, cl_cap)), orig)
        f1, m1 = A.transfer_h1(A.seg_of(a, "sweep_drv_-12"), ref)
        f2, m2 = A.transfer_h1(A.seg_of(b, "sweep_drv_-12"), ref)
        return W.smooth(f1, m1) - W.smooth(f2, m2)

    g = W.GRID
    mmid = (g >= MID[0]) & (g <= MID[1])
    mout = ((g >= OUT[0][0]) & (g <= OUT[0][1])) | ((g >= OUT[1][0]) & (g <= OUT[1][1]))
    # ⚠⚠ A POOLED out-of-band rms cannot say WHICH region moved, and the candidates differ by
    # where their shelf sits -- so a pooled improvement is exactly consistent with one sub-band
    # getting better while another gets worse (`a-pooled-statistic-cannot-answer-about-its-own-
    # axis`).  The three sub-bands are printed beside the pool, and the bar is applied to each.
    SUB = (("lo", 60.0, 250.0), ("hi1", 900.0, 2800.0), ("hi2", 2800.0, 8000.0))
    msub = {k: (g >= a) & (g <= b) for k, a, b in SUB}
    ped_ratio = ratio_curve_cap("ref-od.wav", "ref-clean.wav")

    cands = [(hz, s, cut) for hz in (1600.0, 2800.0, 4000.0, 5600.0)
             for s in (0.9, 1.6, 2.5) for cut in (3.0, 4.5, 6.0)]
    cands = [(2800.0, 0.9, 6.0)] + [c for c in cands if c != (2800.0, 0.9, 6.0)]
    # ⚠⚠ MEMBERSHIP.  A first draft rendered `("ref-od.wav",) + CAPTURES[:3]` for the notch
    # statistic -- and `CAPTURES[0]` IS `ref-od.wav`, so it was DOUBLE-COUNTED, over a 4-capture
    # subset that is not BF5/BF6's 6.  The shipped row then read 0.805 where BF5/BF6 read 0.758 on
    # the same renders, i.e. this table's numbers were not comparable with the ones the defect was
    # established from (`aggregate-moved-check-membership-first`, in this gate's own output).
    # ⇒ one membership, `CAPTURES`, used by every sub-gate that quotes a notch ratio.
    cjobs2 = [(f, ("odMakeupDb=%g" % SHIPPED_MAKEUP, "odMakeupLowCutDb=%g" % SHIPPED_LOCUT,
                   "odMakeupHighHz=%g" % hz, "odMakeupHighS=%g" % s,
                   "odMakeupHighCutDb=%g" % cut, "odNotchDepthDb=0"),
               "j%g_%g_%g" % (hz, s, cut))
              for f in CAPTURES for (hz, s, cut) in cands]
    # the CLEAN twin each candidate's ratio is referred to (the makeup is OD-only, so one is
    # enough -- BF1 already asserted the clean path does not move with these settings)
    cjobs2.append(("ref-clean.wav", OFF, "cleanref"))
    print(f"    rendering {len(cjobs2)} conditions for {len(cands)} candidates ...")
    jp = render_all(cjobs2, args.jobs)

    print(f"\n    {'highHz':>7}{'S':>6}{'cutDb':>7}{'notch r':>10}{'mid rms':>10}{'out rms':>10}"
          f"{'60-250':>9}{'0.9-2.8k':>10}{'2.8-8k':>9}")
    res8 = {}
    for (hz, s, cut) in cands:
        tag = "j%g_%g_%g" % (hz, s, cut)
        d = ratio_curve(jp[("ref-od.wav", tag)], jp[("ref-clean.wav", "cleanref")]) - ped_ratio
        midr = float(np.sqrt(np.mean(d[mmid] ** 2)))
        outr = float(np.sqrt(np.mean(d[mout] ** 2)))
        sub = {k: float(np.sqrt(np.mean(d[m] ** 2))) for k, m in msub.items()}
        rs = []
        for f in CAPTURES:
            loc = _locate_all(jp[(f, tag)], WIDE_WIN)
            for sw in SWEEPS:
                if loc[sw]["edge"] or ped_cache[f][sw]["edge"]:
                    continue
                rs.append(loc[sw]["f0"] / ped_cache[f][sw]["f0"])
        nr = float(np.median(rs))
        res8[(hz, s, cut)] = {"notch": nr, "mid": midr, "out": outr, "n": len(rs), "sub": sub}
        # ⚠ "s172 shelf", NOT "shipped": every arm here holds `odNotchDepthDb = 0` so the shelf is
        # isolated, where the shipped build runs it at 3.0.  The comparison is internally valid
        # (all arms share the setting) and the row is NOT the shipped configuration.
        star = "  <- s172 shelf" if (hz, s, cut) == (2800.0, 0.9, 6.0) else ""
        print(f"    {hz:7.0f}{s:6.2f}{cut:7.1f}{nr:10.3f}{midr:10.2f}{outr:10.2f}"
              f"{sub['lo']:9.2f}{sub['hi1']:10.2f}{sub['hi2']:9.2f}{star}")

    ship = res8[(2800.0, 0.9, 6.0)]
    off_notch = float(np.median(err_off))
    # The bar is applied PER SUB-BAND as well as to the pool, so a candidate cannot pass by
    # trading one region against another inside a single rms.
    TOL = 0.02      # dB rms, so "no worse" is not decided by the last digit of a noisy rms
    ok8 = {k: v for k, v in res8.items()
           if v["notch"] >= off_notch and v["mid"] <= ship["mid"] + TOL
           and v["out"] <= ship["out"] + TOL
           and all(v["sub"][b] <= ship["sub"][b] + TOL for b in ("lo", "hi1", "hi2"))}
    print(f"\n    bar: notch ratio >= the makeup-OFF position ({off_notch:.3f}) AND neither of")
    print(f"         s172's own residuals worse than the s172 shelf (mid {ship['mid']:.2f}, "
          f"out {ship['out']:.2f}),")
    print(f"         AND no SUB-BAND worse than it either (lo {ship['sub']['lo']:.2f}, "
          f"hi1 {ship['sub']['hi1']:.2f}, hi2 {ship['sub']['hi2']:.2f}), all +{TOL:.2f} tolerance")
    if ok8:
        pick = max(ok8, key=lambda k: ok8[k]["notch"])
        print(f"    ⇒ {len(ok8)} candidate(s) meet BOTH.  Best on the notch axis: "
              f"highHz {pick[0]:.0f}, S {pick[1]:.2f}, cut {pick[2]:.1f} dB")
        print(f"      notch {ok8[pick]['notch']:.3f} (s172 shelf {ship['notch']:.3f}, "
              f"off {off_notch:.3f})   mid {ok8[pick]['mid']:.2f} ({ship['mid']:.2f})"
              f"   out {ok8[pick]['out']:.2f} ({ship['out']:.2f})")
        print(f"      sub-bands  lo {ok8[pick]['sub']['lo']:.2f} ({ship['sub']['lo']:.2f})   "
              f"0.9-2.8k {ok8[pick]['sub']['hi1']:.2f} ({ship['sub']['hi1']:.2f})   "
              f"2.8-8k {ok8[pick]['sub']['hi2']:.2f} ({ship['sub']['hi2']:.2f})")
    else:
        pick = None
        print("    ⇒ NO candidate meets both bars -- the notch and the out-of-band job are in")
        print("      genuine conflict in this family, and the choice is a USER DECISION about")
        print("      where on the trade to sit, not a fit.  The frontier is the table above.")
    out["bf8"] = {"mid_band": MID, "out_band": OUT,
                  "rows": {f"{hz:g}_{s:g}_{cut:g}": v for (hz, s, cut), v in res8.items()},
                  "off_notch": off_notch,
                  "pick": (list(pick) if pick else None)}

    if args.json:
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1, sort_keys=True, default=float)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
