#!/usr/bin/env python3.11
"""GATE AE -- the 4.5-6 kHz null: PRESENCE or ABSENCE, asked of the log-f locator.  Session 133.

WHY THIS EXISTS
---------------
Session 131's GATE AD (AD5b) measured this feature's DEPTH on the report's ~1/3-octave grade grid
and found the two sides doing completely different things across the driven ladder:

    ND    depth RISES monotonically with drive in 3 of 3 GRUNT positions (spans 2.60/7.55/3.41 dB;
          at GRUNT cut it runs 0.92 -> 2.19 -> 8.47 dB)
    model depth FROZEN -- span 0.01 dB in all three, sitting at 0.69-0.70 dB

and drew the correct inference from it: **a prominence that is both tiny AND invariant to every
control is the signature of NO FEATURE, not of a pinned one** (s126 -- an extremum-finder always
returns something).  It then said, in as many words, that confirming that needs GATE W's log-f
locator rather than its own grid, and put it at the head of its own NEXT list as "the cheapest
high-value read on the board".  This gate is that read.

⚠⚠ AND IT IS NOT A FOREGONE CONCLUSION, BECAUSE `UNRESOLVED` HAS BITTEN THIS PROJECT BEFORE ON
EXACTLY THIS FEATURE'S NEIGHBOUR.  Session 126 found GATE W6 reporting the model's BASS PEAK
`UNRESOLVED` on the stimulus axis -- and that silence was a **membership** property, not a physical
one: W6 reads the BLEED-FREE endpoints, the bass peak is a MIX CANCELLATION, and a cancellation has
no bleed-free reading at all, by the same physics W5/W7 classified it with.  Measured on a capture
that HAS a mix, the feature was there and moving.

GATE W's own stored s122 run says the same thing about THIS feature, and nothing has read it back:

    w4  treble_notch  model span  3.7 % over 3 detents -> NETWORK
                      pedal span 44.1 % over 6 detents -> MIX          (agreement: DISAGREE)
    w6  treble_notch  model medians []  -> UNRESOLVED
                      pedal 8569 -> 10470 -> 8964 -> 7207 Hz -> DRIVE-DEPENDENT
    w7  treble_notch  class "(b) MIX / BALANCE" ... "the feature VANISHES bleed-free"

AD5b reads the BLEED-FREE class.  So there are two live hypotheses and they have opposite
consequences for open work item 6:

    (H1) MISSING FEATURE.  The model has no interior extremum in this region under any condition.
         Then item 6 gains a presence/absence instance -- a different KIND of fix from a centre or
         a depth, and the sharpest one on the board.
    (H2) MEMBERSHIP.  The model's feature is a MIX cancellation, so it is absent bleed-free BY
         PHYSICS and present where a mix exists.  Then AD5b's "frozen 0.69 dB" is s126's trap
         repeated, "we appear to have no null here at all" must be withdrawn as stated, and what
         survives is the (still real, still unowned) fact that the PEDAL has a deep bleed-free
         feature here and we have only a cancellation.

Only a reading on the LEVEL ladder can tell them apart, so this gate reads both.

⛔ WHAT THIS GATE DOES NOT DO
----------------------------
* It grades NOTHING against hardware.  `reference-sources.md` §1 gives the 5-6 kHz null to
  **neither** reference ("Neither -- unresolved"), and §3's driven charts disagree between
  conditions.  AD5b prints that exclusion every run and so does this.
* It proposes no constant and fits nothing.  It reports presence, position and depth per condition.
* It does not claim to know what the PEDAL's feature is made of.  ND is a black box; for the
  reference this gate reports signatures (the LEVEL dose-response, the drive dose-response) and
  what they are consistent with -- GATE W's own rule.

THE SUB-GATES  (hard exits cover this gate's OWN validity only; every physics outcome is a
COMPUTED verdict and execution continues -- s108's rule)
-------------------------------------------------------------------------------------------
AE0  PROVENANCE + MEMBERSHIP, asserted from SETTINGS and never from a filename substring (s114).
     Three outcomes, not two (s129): complete / PARTIAL -> refuse / absent -> excluded with its
     physical reason printed.
AE1  KNOWN ANSWERS, three, before a single prominence is read:
     (a) GATE W's own W1, re-run under the CURRENT binary -- the shared locator must still
         reproduce GATE R's stored notch frequencies AND follow the R-C scaling law.  Imported and
         CALLED, not re-derived, so the two gates cannot drift.
     (b) THE ONE THAT MAKES THIS GATE NON-VACUOUS: `_best_interior` must FIND features that ARE
         there, at the very conditions AE3 reads.  A silent estimator and an absent feature are
         indistinguishable (s126) -- so the treble PEAK and the bridged-T notch are located by the
         same call, on the same curves, and are required to come back with real prominence.
     (c) Cross-instrument: the fine grid must reproduce AD5b's coarse-grid ORDERING (pedal deeper
         than model) at AD5b's own membership.  ORDERING ONLY -- the two estimators use different
         grids and different prominence definitions and must not be compared by value.
AE2  WINDOW VALIDITY, and where the feature actually sits.  A vertex on a window bound is a bound,
     not a measurement.  ⚠ Also prints the plain fact that on BOTH sides this feature sits well
     ABOVE the "4.5-6 kHz" the chart review named it by.
AE3  THE HEADLINE -- bleed-free presence/absence across the driven ladder x GRUNT, both sides.
     The threshold-free discriminator is `n_interior`: zero interior local minima across the whole
     window means the curve is monotone there, i.e. no notch, with no bar to argue about.
AE4  THE MIX BRANCH -- the same feature on the LEVEL ladder, where a cancellation CAN appear.
     This is what discriminates H1 from H2 and it is the reason this gate exists.
AE5  THE COMPUTED VERDICT.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                 # noqa: E402
import captures as C                # noqa: E402
import feature_locus_gate as W      # noqa: E402  (the locator, the grid, the named windows)
import bass_peak_locus as Y         # noqa: E402  (s126's INTERIOR-extremum estimator)
import hw_trend_gate as AD          # noqa: E402  (AD5b's own membership and window)
import matrix_grade as MG           # noqa: E402
import od_absolute_gate as Q        # noqa: E402

REPORT = "analysis/reports/s124_ship.json"
OUT_JSON = "analysis/reports/s133_hf_null.json"
REN_DIR = "build/s133_hf_null"

# THE FEATURE, taken from GATE W's own table rather than typed -- the window is a NAMED claim about
# where this feature lives and it must be ONE definition across the two gates.
FEATURE = "treble_notch"
KIND = W.FEAT_BY_NAME[FEATURE][1]
WINDOW = W.FEAT_BY_NAME[FEATURE][2]
LABEL = W.FEAT_BY_NAME[FEATURE][3]

# AE1b's control, and the one this gate's first draft got WRONG.
#
# `treble_peak` -- s125's closed-form-localised ~2935 Hz vertex (measured 2977-2983) -- is
# established present ON EXACTLY THIS CONDITION CLASS: GATE W6 reads it on the bleed-free OD
# endpoints at all four stimulus rungs and reports it FIXED to 0.2 %, which it could not do unless
# every one of those readings had passed W3's own edge/prominence guards.  It is also the NEAREST
# NEIGHBOUR of the feature under test -- same curve, same smoothing, the adjacent window -- which
# is the strongest kind of not-silent control available.
NOT_SILENT_CONTROL = "treble_peak"
#
# ⚠⚠ `bt_notch` IS NOT A CONTROL, AND THE REASON IS ON THE RECORD ALREADY.  This gate's first draft
# used it as one and the run refused: the 716 Hz bridged-T reads **0.13 dB** on the MODEL at some
# bleed-free driven conditions.  That is not a discovery -- GATE W's own W1a comment says in as
# many words that at `sweep_clean` "the bridged-T notch has a prominence of 0.46 dB and is barely a
# feature at all", and s131's AD5 measured its DEPTH moving across the drive ladder on the ND side.
# So it was never established present at the conditions THIS gate reads, and including it was a
# defect in the test, not in the model.  It is still READ and PRINTED below (its numbers are
# informative) and it is excluded from the pass/fail by name, with this reason, so the exclusion is
# a pre-registered consequence of prior knowledge rather than a reaction to this run's numbers.
# ⭐ GENERAL, and the reason this is written out at length: a control must be established present
# AT THE CONDITIONS THE GATE READS, not merely somewhere.
FAINT_NON_CONTROL = "bt_notch"
PRESENT_CONTROLS = (NOT_SILENT_CONTROL, FAINT_NON_CONTROL)

# AE1b(iii) -- the SYNTHETIC arm, which is what actually makes "no interior extremum" a statement
# about the curve rather than about the code.  A notch of known depth is injected into the MODEL's
# own bleed-free curve and the estimator must find it; at depth 0 it must find nothing, which is
# the arm's own built-in mutation control.
INJECT_DB = (0.0, 1.0, 3.0, 9.0)

# The name the chart review gave this feature.  Printed against where it is actually measured --
# a label is not a window (AE2).
CHART_NAME_HZ = (4500.0, 6000.0)

SWEEPS = W.SWEEPS
DRIVEN = AD.DRIVEN
GRUNT_NAME = AD.GRUNT_NAME

# ⚠ NOT a new bar.  GATE W's own "a located centre is only a measurement while the feature has some
# depth" threshold, imported so the two gates cannot drift, and swept in AE3 with the surviving
# count asserted to change (s106 N5).
MIN_PROM_DB = W.MIN_PROM_DB
PROM_SWEEP = W.PROM_SWEEP
EDGE_MARGIN_FRAC = W.EDGE_MARGIN_FRAC

# AE1b: "the same reading" on the locator's own grid.  A third of a cell, the project's existing
# bar (s129), taken from the tool that DEFINES the cell rather than transcribed.
SAME_READING_FRAC = W.GRID_STEP_FRAC / 3.0


def die(tag, msg):
    """Refuse with exit code 2, NOT 1.

    ⚠ An uncaught exception also exits 1, so a runner scoring `rc != 0` cannot tell a guard that
    fired from a gate that crashed -- s117's "check guard IDENTITY, not just non-zero exit",
    enforced at the source instead of only in the runner.  2 means "a guard refused"; 1 means
    "this fell over"."""
    sys.stderr.write(f"GATE {tag}: {msg}\n")
    sys.exit(2)


# =============================================================================================
# data
# =============================================================================================
def read_side(al, sw, ref):
    """One (side, capture, sweep) cell: the smoothed log-f curve, then BOTH estimators on it.

    `narrow` is GATE W's `locate` -- the argmin of the window, which always returns something.
    `wide`   is s126's `_best_interior` -- the most prominent INTERIOR local extremum, which can
             legitimately return "there is no extremum here at all" (`n_interior == 0`).
    Both run on the SAME curve from the SAME smoothing, so any difference between them is the
    estimator and nothing else."""
    f, m = A.transfer_h1(A.seg_of(al, sw), ref)
    d = W.smooth(f, m)
    # The level of the curve itself, so AE4 can MEASURE the LEVEL-min mute rather than assume it.
    # GATE W2's own rule: "excluded because we expect silence" is how a genuinely broken render
    # gets waved through.
    out = {"peak_db": float(np.max(d))}
    for name in (FEATURE,) + PRESENT_CONTROLS:
        kind, win = W.FEAT_BY_NAME[name][1], W.FEAT_BY_NAME[name][2]
        nar = W.locate(d, win, kind)
        wid = Y._best_interior(d, win, kind)
        out[name] = {"narrow": nar, "wide": wid}
    return out


def _cell(args):
    fname, ren_dir = args
    orig, ref = W._load_orig()
    ra = C.render_args(C.parse_capture(fname))
    out = os.path.join(ren_dir, fname.replace(".wav", "") + "_plugin.wav")
    W.render(out, ra)
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    rec = {"file": fname, "model": {}, "pedal": {}}
    for sw in SWEEPS:
        rec["model"][sw] = read_side(ren_al, sw, ref)
        rec["pedal"][sw] = read_side(cap_al, sw, ref)
    return rec


def collect(files, jobs):
    from parallel import pmap
    rows = pmap(_cell, [(f, REN_DIR) for f in files], jobs=jobs)
    return {r["file"]: r for r in rows}


# =============================================================================================
# AE0  PROVENANCE + MEMBERSHIP
# =============================================================================================
def gate_ae0(rep):
    print("=" * 94)
    print("AE0  PROVENANCE + MEMBERSHIP -- asserted from SETTINGS, never from a filename")
    print("=" * 94)

    name = os.path.basename(rep.path)
    meta = rep.d.get("meta", {})
    if meta.get("fit_overrides"):
        die("AE0", f"{name} was rendered with --fit {meta['fit_overrides']} -- that is not the "
                   "shipped model, so nothing below describes what we ship.")
    print(f"  report                 {name}  ({len(rep.captures)} captures, shipped constants)")
    print(f"  feature                {FEATURE}  -- {LABEL}")
    print(f"  window (GATE W's own)  {WINDOW[0]:.0f} .. {WINDOW[1]:.0f} Hz   kind={KIND}")
    print(f"  grid                   1/{W.GRID_FRAC} oct = {W.GRID_STEP_FRAC*100:.2f} % per cell, "
          f"{W.F_LO:.0f} .. {W.F_HI:.0f} Hz")

    caps = {c["file"]: c for c in rep.captures}

    # (1) THE BLEED-FREE CLASS -- GATE Q's own endpoint selection, so the dropout handling and the
    #     `gain-n12` exclusion cannot drift from the chain every OD number is quoted against.
    eps = Q.endpoints_od(caps)
    if len(eps) != W.R.EXPECT_ENDPOINTS:
        die("AE0", f"GATE Q's endpoint count moved ({len(eps)} vs {W.R.EXPECT_ENDPOINTS}) -- bump "
                   "it there DELIBERATELY after checking what arrived, do not re-point it here")
    bleed = [e for e in eps if not MG.is_gain_n12(e)]
    n12 = [e for e in eps if MG.is_gain_n12(e)]
    print(f"\n  bleed-free OD endpoints   {len(eps)} (GATE Q's selection, "
          f"expected {W.R.EXPECT_ENDPOINTS})")
    print(f"      graded here           {len(bleed)}")
    print(f"      `gain-n12` excluded   {len(n12)} -- a SECOND operating point (s108 P4), not a "
          f"defect; named, not silently dropped")

    # (2) THE LEVEL LADDER -- AE4's whole point.  Resolved by SETTINGS: LEVEL noon is `ref-od.wav`,
    #     so a name transform can only ever see part of it (s112).
    lad = W.level_ladder(caps)
    print(f"\n  LEVEL ladder              {len(lad)} detents  {sorted(lad)}")
    for lv, f in lad.items():
        print(f"      LEVEL {lv:<6.3f}          {f}")
    if len(lad) < 6:
        die("AE0", f"the LEVEL ladder has only {len(lad)} detents -- AE4's dose-response IS this "
                   "gate's discriminator, and a short ladder is a membership defect")
    # LEVEL min is excluded for a MEASURED physical reason, printed rather than assumed.
    print(f"      (LEVEL min: the MODEL MUTES there -- GATE L7's second [ENG] divider -- so it "
          f"carries no locatable feature on our side at all)")

    # (3) AD5b's OWN membership, for the AE1c cross-instrument known answer.  Reproduced with AD's
    #     imported predicates so the two gates select the same rows.
    ad_groups = {}
    for gi in (0, 1, 2):
        ad_groups[gi] = rep.select(
            lambda s, gi=gi: s.get("gruntIdx") == gi and AD.bleed_free(s)
            and s.get("distEngage") is True and AD.flat_eq(s))
    print(f"\n  AD5b's groups (for AE1c only, via AD's own predicates):")
    for gi in (0, 1, 2):
        print(f"      GRUNT {GRUNT_NAME[gi]:<6s}          n={len(ad_groups[gi])}")
        if not ad_groups[gi]:
            die("AE0", f"AD5b's GRUNT {GRUNT_NAME[gi]} group is EMPTY -- the cross-instrument "
                       "known answer has nothing to reproduce, which is `empty-gate-must-fail`")

    files = sorted(set(bleed) | set(lad.values()))
    print(f"\n  captures to render        {len(files)}")
    return caps, bleed, lad, ad_groups, files


# =============================================================================================
# AE1  KNOWN ANSWERS
# =============================================================================================
def gate_ae1a(out, jobs):
    """(a) GATE W's own W1, re-run under the CURRENT binary.  Imported and CALLED."""
    print("\n" + "=" * 94)
    print("AE1a  KNOWN ANSWER -- GATE W's locator, re-certified under the CURRENT binary")
    print("=" * 94)
    print("  ⚠ Re-RUN rather than read from the stored s122 report: that report was rendered")
    print("    against `s120_newton.json`'s binary, and a known answer inherited across a")
    print("    baseline epoch certifies the wrong build (`rebaseline-all-derived-artefacts`,")
    print("    s118's baseline-EPOCH form).  W1 exits on failure; if it returns, the shared")
    print("    locator reproduces GATE R's frequencies AND follows the R-C scaling law here.")
    res = W.gate_w1(out, jobs)
    print(f"  -> locator resolution {res*100:.2f} % (its own measured agreement)")
    return res


def curve_of(fname, side, sw):
    """The smoothed log-f curve for one (capture, side, sweep) -- the same path `read_side` uses."""
    orig, ref = W._load_orig()
    if side == "model":
        al, _ = A.align(A.load(os.path.join(
            REN_DIR, fname.replace(".wav", "") + "_plugin.wav")), orig)
    else:
        al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    f, m = A.transfer_h1(A.seg_of(al, sw), ref)
    return W.smooth(f, m)


def gate_ae1b(rows, bleed, out):
    """(b) THE ONE THAT MAKES THIS GATE NON-VACUOUS: the estimator is not silent, and not capped.

    `_best_interior` returning nothing for `treble_notch` is only evidence about the MODEL if the
    same call, on the same curves, at the same conditions, finds features that ARE there and
    reports their real depth.  s126's Y7b learned this the hard way and stated it: "a silent
    estimator and an absent feature are indistinguishable until you show the estimator finds the
    feature when it is there."  Three arms, because one is not enough:

      (i)   NOT SILENT -- the nearest-neighbour control, at every graded condition.
      (ii)  NOT CAPPED, on real data -- what the estimator returns in THIS window on the side that
            has a feature.  Printed without a bar (a bar here would be a number I guessed), and it
            reads the REFERENCE only, so it cannot be circular about the model.
      (iii) SYNTHETIC -- a notch of known depth injected into the MODEL's own curve.  This is the
            direct falsifier of "n_interior == 0 is a code artefact", and its zero-depth rung is
            its own built-in mutation control.
    """
    print("\n" + "=" * 94)
    print("AE1b  KNOWN ANSWER -- the estimator is NOT SILENT and NOT CAPPED")
    print("=" * 94)

    # ---- (i) not silent ------------------------------------------------------------------------
    print(f"  (i) NOT SILENT.  Control = `{NOT_SILENT_CONTROL}` on the MODEL, every graded cell.")
    print(f"      bar: within {SAME_READING_FRAC*100:.2f} % of `locate`'s centre (1/3 of a grid "
          f"cell, s129's bar, imported from the tool that defines the cell)")
    print(f"           AND prominence >= {MIN_PROM_DB:.1f} dB (GATE W's own MIN_PROM_DB)")
    worst_d, worst_p, n = 0.0, 1e9, 0
    for cap in bleed:
        for sw in DRIVEN:
            v = rows[cap]["model"][sw][NOT_SILENT_CONTROL]
            nar, wid = v["narrow"], v["wide"]
            if not np.isfinite(wid["f0"]) or wid["n_interior"] == 0:
                die("AE1b", f"the interior estimator found NO extremum for "
                            f"`{NOT_SILENT_CONTROL}` on the MODEL at {cap} / {sw} -- GATE W6 "
                            "resolves that feature on these very endpoints at all four rungs, so "
                            "the estimator, not the model, is what this gate would be measuring")
            worst_d = max(worst_d, abs(wid["f0"] - nar["f0"]) / nar["f0"])
            worst_p = min(worst_p, wid["prom"])
            n += 1
    print(f"      {n} readings: worst centre disagreement {worst_d*100:.2f} %, "
          f"smallest prominence {worst_p:.2f} dB")
    if worst_d > SAME_READING_FRAC:
        die("AE1b", f"the two estimators disagree by {worst_d*100:.2f} % on `"
                    f"{NOT_SILENT_CONTROL}` (> {SAME_READING_FRAC*100:.2f} %) -- they are not "
                    "tracking the same vertex, so a disagreement below would mean nothing")
    if worst_p < MIN_PROM_DB:
        die("AE1b", f"the interior estimator returns only {worst_p:.2f} dB on `"
                    f"{NOT_SILENT_CONTROL}` (< {MIN_PROM_DB:.1f} dB) -- it reads faint "
                    "everywhere, so a faint reading below would be the estimator's property")

    # the pre-registered NON-control, printed rather than hidden
    fp = [rows[c]["model"][s][FAINT_NON_CONTROL]["wide"]["prom"] for c in bleed for s in DRIVEN]
    print(f"      (`{FAINT_NON_CONTROL}` is NOT a control -- see the constant.  Its model "
          f"prominence here: {min(fp):.2f} .. {max(fp):.2f} dB,")
    print(f"       i.e. below the bar at its worst, exactly as GATE W's own W1a comment records.  "
          f"Printed, excluded by name, not silently dropped.)")

    # ---- (ii) not capped, on real data ---------------------------------------------------------
    rp = [rows[c][s][sw][FEATURE]["wide"]["prom"]
          for c in bleed for s in ("pedal",) for sw in DRIVEN]
    print(f"\n  (ii) NOT CAPPED (real data, REFERENCE side only, same window, same call):")
    print(f"       ND `{FEATURE}` prominence over {len(rp)} graded cells: "
          f"{min(rp):.2f} .. {max(rp):.2f} dB, median {np.median(rp):.2f}")
    print(f"       No bar -- a bar here would be a number I guessed.  (iii) carries the gate.")

    # ---- (iii) synthetic -----------------------------------------------------------------------
    ref_cap, ref_sw = sorted(bleed)[0], DRIVEN[-1]
    d0 = curve_of(ref_cap, "model", ref_sw)
    lo, hi = WINDOW
    fc = float(np.sqrt(lo * hi))
    width = 3.0 * W.GRID_STEP_FRAC                     # ~3 grid cells, in log-f
    bump = np.exp(-((np.log(W.GRID / fc) / width) ** 2))
    print(f"\n  (iii) SYNTHETIC -- inject a notch into the MODEL's own curve "
          f"({ref_cap}, {ref_sw})")
    print(f"        centre {fc:.1f} Hz (the window's geometric centre, not chosen by looking), "
          f"half-width ~3 cells")
    print(f"        {'depth in':>9s} {'n_interior':>11s} {'f0 out':>9s} {'err':>7s} "
          f"{'prom out':>9s}")
    inj = []
    for D in INJECT_DB:
        r = Y._best_interior(d0 - D * bump, WINDOW, KIND)
        err = (abs(r["f0"] - fc) / fc) if np.isfinite(r["f0"]) else float("nan")
        inj.append({"depth_db": D, "n_interior": r["n_interior"], "f0": r["f0"],
                    "err_frac": err, "prom_db": r["prom"]})
        f0s = "      nan" if not np.isfinite(r["f0"]) else f"{r['f0']:9.1f}"
        errs = "    nan" if not np.isfinite(err) else f"{err*100:6.2f}%"
        print(f"        {D:9.1f} {r['n_interior']:11d} {f0s} {errs} {r['prom']:9.2f}")
    zero = inj[0]
    if zero["n_interior"] != 0:
        die("AE1b", f"the ZERO-depth rung of the synthetic arm found {zero['n_interior']} interior "
                    "extremum/extrema -- the arm's own mutation control has failed, so the whole "
                    "injection test is vacuous and AE3's headline is unvalidated")
    proms = [r["prom_db"] for r in inj]
    if not all(b > a for a, b in zip(proms, proms[1:])):
        die("AE1b", f"recovered prominence is not monotone in injected depth ({proms}) -- the "
                    "estimator does not measure depth, so no depth below is quotable")
    for r in inj[1:]:
        if r["n_interior"] == 0:
            die("AE1b", f"a {r['depth_db']:.1f} dB injected notch was NOT FOUND "
                        "(n_interior=0) -- the estimator cannot find a notch that IS there in "
                        "this window, so AE3's zero counts are the estimator's property")
    # ⚠⚠ THE CENTRE BAR IS A LAW, NOT A NUMBER, AND THE FIRST DRAFT'S FLAT TOLERANCE WAS WRONG.
    # A vertex sitting on a sloping background is pulled by (slope / curvature) -- s122's own
    # mutation note, in its other direction.  A Gaussian notch of depth D and log-f half-width w
    # has curvature 2D/w^2 at its bottom, so the offset goes as w^2*slope/(2D), i.e. as 1/D: a
    # SHALLOW notch on this steeply rolling-off curve is *expected* to read off-centre, and a flat
    # tolerance therefore fails a correct estimator at the shallow end (measured 2.81 % at 1 dB).
    # Gating the SCALING instead tests the mechanism rather than asserting a number
    # (`derive-the-bar-from-the-quantity's-own-scaling-law`), and it is the STRICTER test: it must
    # fall at every rung AND land inside a cell once the notch is deep enough to dominate.
    errs = [r["err_frac"] for r in inj[1:]]
    if not all(b < a for a, b in zip(errs, errs[1:])):
        die("AE1b", f"the recovered centre's error does not FALL with injected depth "
                    f"({[round(e*100, 2) for e in errs]} %) -- that is the slope/curvature law "
                    "this estimator must obey on a sloping background; if it does not, the bias "
                    "is not the background and the vertex fit is wrong")
    if inj[-1]["err_frac"] > W.GRID_STEP_FRAC:
        die("AE1b", f"even a {inj[-1]['depth_db']:.1f} dB notch is recovered "
                    f"{inj[-1]['err_frac']*100:.2f} % off its injected centre "
                    f"(> one {W.GRID_STEP_FRAC*100:.2f} % cell) -- the vertex fit is biased "
                    "beyond what the background slope explains")
    pred = [errs[0] * inj[1]["depth_db"] / r["depth_db"] for r in inj[1:]]
    print(f"        ⇒ 0 dB -> NOTHING found; every D > 0 -> FOUND, prominence monotone in depth,")
    print(f"          centre error falling as the 1/D law predicts: measured "
          f"{'/'.join(f'{e*100:.2f}' for e in errs)} % vs "
          f"{'/'.join(f'{p*100:.2f}' for p in pred)} % predicted (anchored at the shallowest).")
    print(f"        ⚠ Recovered prominence is a LOWER bound by construction: the walk terminates "
          f"where the falling background passes below the notch bottom, so a deep notch on a")
    print(f"          rolling-off curve reads short (9.0 dB in -> {inj[-1]['prom_db']:.2f} out).  "
          f"The arm certifies FINDING and ORDERING, which is all AE3 rests on -- not depth.")
    print(f"\n  -> the estimator finds what is there and reports nothing when nothing is there.  "
          f"A null reading below is about the DEVICE.")
    out["ae1b"] = {"n": n, "worst_centre_frac": worst_d, "min_prom_db": worst_p,
                   "bar_frac": SAME_READING_FRAC, "bar_prom_db": MIN_PROM_DB,
                   "faint_non_control": {"name": FAINT_NON_CONTROL,
                                         "model_prom_db": [float(min(fp)), float(max(fp))]},
                   "nd_prom_db": [float(min(rp)), float(max(rp))],
                   "synthetic": {"capture": ref_cap, "sweep": ref_sw, "centre_hz": fc,
                                 "rungs": inj}}
    return inj


def gate_ae1c(rep, ad_groups, rows, out):
    """(c) Cross-instrument: reproduce AD5b's ORDERING on a grid 18x finer.

    ⚠ ORDERING ONLY.  AD5b reads a ~1/3-octave grade grid and defines depth as
    `mean(curve at the two window edges) - curve at the chosen interior band`; this gate reads a
    1/48-octave log grid and defines it as a two-sided interior prominence.  Those are different
    quantities and `a-ratio-between-two-instruments-inherits-both` -- the two must not be compared
    by VALUE.  What they must agree on is which side is deeper, which is the whole of AD5b's claim.

    ⚠ AD5b's estimator is transcribed here rather than imported, deliberately: `gate_hf_null` does
    not factor it out, and re-pointing that gate to expose it would be an edit to a passing gate in
    a session that is not about it.  The two constants it needs (the window and the driven sweeps)
    ARE imported, so the only transcribed thing is the two-line rule itself.
    """
    print("\n" + "=" * 94)
    print("AE1c  KNOWN ANSWER -- the fine grid reproduces AD5b's ORDERING (not its values)")
    print("=" * 94)
    lo_hz, hi_hz = AD.HF_NULL_WINDOW
    interior = [f for f in rep.bands if lo_hz < f < hi_hz]
    ilo, ihi = rep.idx(lo_hz), rep.idx(hi_hz)
    icand = [rep.idx(f) for f in interior]
    print(f"  AD5b window {lo_hz:.1f} .. {hi_hz:.1f} Hz;  interior bands {interior}")
    print(f"  this gate   {WINDOW[0]:.0f} .. {WINDOW[1]:.0f} Hz on a 1/{W.GRID_FRAC}-oct grid")
    print()
    print(f"  {'GRUNT':>6} {'sweep':>14}   {'--- AD5b coarse ---':>21}   "
          f"{'--- AE fine ---':>19}   ordering")
    print(f"  {'':>6} {'':>14}   {'model':>9} {'ND':>9}   {'model':>9} {'ND':>9}")
    agree = total = ties = 0
    cells = []
    for gi in (0, 1, 2):
        for sw in DRIVEN:
            mc, rc = [], []
            for c in ad_groups[gi]:
                got = rep.raw(c, sw)
                if got is None:
                    continue
                mc.append(got[0])
                rc.append(got[1])
            if not mc:
                continue
            pm = np.nanmedian(np.array(mc), axis=0)
            pr = np.nanmedian(np.array(rc), axis=0)

            def coarse(curve):
                j = min(icand, key=lambda k: curve[k])
                return float(np.nanmean([curve[ilo], curve[ihi]]) - curve[j])

            cm, cr = coarse(pm), coarse(pr)
            # ⚠ TIE, not INVERSION.  Where the fine estimator returns EXACTLY 0.00 on both sides
            # there is no ordering to reproduce -- `fr > fm` is False and so is `fm > fr`, and
            # scoring that as a disagreement would book "neither side has a feature" as an
            # instrument conflict.  A tie is reported as a tie and excluded from the agreement
            # count, with its own line, rather than being silently folded either way.
            # the fine read, over the same rows this gate actually rendered
            fm, fr = [], []
            for c in ad_groups[gi]:
                f = c["file"]
                if f not in rows:
                    continue
                fm.append(rows[f]["model"][sw][FEATURE]["wide"]["prom"])
                fr.append(rows[f]["pedal"][sw][FEATURE]["wide"]["prom"])
            if not fm:
                continue
            fm_, fr_ = float(np.median(fm)), float(np.median(fr))
            tie = (fm_ == fr_)
            ok = None if tie else ((cr > cm) == (fr_ > fm_))
            if tie:
                ties += 1
                mark = "— TIE (both 0.00 on the fine grid: no ordering to reproduce)"
            else:
                agree += ok
                total += 1
                mark = "OK" if ok else "⚠ INVERTED"
            cells.append({"grunt": GRUNT_NAME[gi], "sweep": sw, "coarse_model": cm,
                          "coarse_nd": cr, "fine_model": fm_, "fine_nd": fr_,
                          "tie": bool(tie), "agree": None if tie else bool(ok)})
            print(f"  {GRUNT_NAME[gi]:>6} {sw:>14}   {cm:9.2f} {cr:9.2f}   "
                  f"{fm_:9.2f} {fr_:9.2f}   {mark}")
    print()
    print(f"  the two instruments agree on WHICH SIDE IS DEEPER in {agree} of {total} "
          f"orderable cells ({ties} tie(s), excluded rather than folded either way).")
    if total == 0:
        die("AE1c", "no cell had an ORDERING to reproduce -- the cross-instrument known answer is "
                    "vacuous, which is `empty-gate-must-fail`")
    if agree < total:
        print(f"  ⚠ {total - agree} cell(s) INVERT.  That is a real disagreement between two")
        print(f"    estimators on the same audio and it must be read before AE3's verdict -- an")
        print(f"    ordering that depends on the grid is not a property of the device.")
    else:
        print(f"  -> the fine grid reproduces AD5b's ordering wherever there is one to reproduce.")
    out["ae1c"] = {"n": total, "agree": agree, "ties": ties, "cells": cells}
    return agree, total


# =============================================================================================
# AE2  WINDOW VALIDITY, and where the feature actually sits
# =============================================================================================
def gate_ae2(rows, bleed, lad, out):
    print("\n" + "=" * 94)
    print("AE2  WINDOW VALIDITY -- a bound is not a measurement; and the LABEL is not the WINDOW")
    print("=" * 94)
    files = sorted(set(bleed) | set(lad.values()))
    edge_rows, seen = [], []
    for f in files:
        for side in ("model", "pedal"):
            for sw in SWEEPS:
                v = rows[f][side][sw][FEATURE]
                nar = v["narrow"]
                seen.append((side, nar["f0"], nar["prom"]))
                if nar["edge"] or nar["margin_frac"] < EDGE_MARGIN_FRAC:
                    edge_rows.append((f, side, sw, nar["f0"], nar["margin_frac"], nar["prom"]))
    print(f"  {len(seen)} (side, capture, sweep) readings of the ARGMIN estimator")
    print(f"  readings resting within {EDGE_MARGIN_FRAC*100:.0f} % of a window bound: "
          f"{len(edge_rows)}")
    for r in edge_rows[:8]:
        print(f"      {r[1]:<6s} {r[0]:<44s} {r[2]:<14s} {r[3]:8.1f} Hz  "
              f"margin {r[4]:.3f}  prom {r[5]:.2f} dB")
    if len(edge_rows) > 8:
        print(f"      ... and {len(edge_rows)-8} more")
    print("  ⚠ These are NOT excluded.  An argmin on a window bound is exactly what a curve with")
    print("    no interior feature produces, so dropping them would delete the evidence this gate")
    print("    exists to weigh.  AE3 reads the INTERIOR estimator, where an edge cannot fake a")
    print("    depth (s126: `locate`'s prominence at a bound is identically 0.00 dB).")

    mf = [f0 for side, f0, _ in seen if side == "model"]
    pf = [f0 for side, f0, _ in seen if side == "pedal"]
    print(f"\n  where the ARGMIN lands, both sides, all conditions:")
    print(f"      model  {min(mf):8.1f} .. {max(mf):8.1f} Hz   (median {np.median(mf):8.1f})")
    print(f"      ND     {min(pf):8.1f} .. {max(pf):8.1f} Hz   (median {np.median(pf):8.1f})")
    print(f"\n  ⚠ THE LABEL IS NOT THE WINDOW.  The chart review named this feature "
          f"'{CHART_NAME_HZ[0]:.0f}-{CHART_NAME_HZ[1]:.0f} Hz'")
    both = mf + pf
    inside = sum(1 for f0 in both if CHART_NAME_HZ[0] <= f0 <= CHART_NAME_HZ[1])
    print(f"    and {inside} of {len(both)} readings on either side fall inside that range.")
    if inside == 0:
        print(f"    ⇒ NOTHING measured here sits at 4.5-6 kHz.  The name comes from "
              f"`reference-sources.md` §3's PNG reads, which §6 says are chart reads with unknown")
        print(f"    conditions; the feature this gate measures is the same one GATE W named")
        print(f"    `treble_notch`, and it lives HIGHER on both sides.  Quote the measured band.")
    out["ae2"] = {"n_readings": len(seen), "n_edge": len(edge_rows),
                  "model_hz": [float(min(mf)), float(max(mf))],
                  "nd_hz": [float(min(pf)), float(max(pf))],
                  "chart_name_hz": list(CHART_NAME_HZ), "n_inside_chart_name": inside}
    return edge_rows


# =============================================================================================
# AE3  THE HEADLINE -- bleed-free presence/absence
# =============================================================================================
def gate_ae3(rows, bleed, caps, out):
    """Is there an interior extremum AT ALL, bleed-free, on each side?

    The threshold-free discriminator is `n_interior`.  `locate` always returns the window's argmin,
    so its silence is uninformative; `_best_interior` returns `n_interior == 0` only when the curve
    is MONOTONE across the entire window, which is a statement no bar can soften.  The prominence
    is reported beside it, and the bar it is judged against is GATE W's own, swept."""
    print("\n" + "=" * 94)
    print("AE3  THE HEADLINE -- bleed-free (BLEND = LEVEL = 1), driven ladder x GRUNT")
    print("=" * 94)
    print("  At BLEND = LEVEL = 1 the clean coefficient is exactly 0 (GATE K2's two exact zeros),")
    print("  so anything here belongs to the OD path alone -- and a MIX cancellation cannot appear")
    print("  at all.  That is the whole reason AE4 exists.")
    print()
    by_grunt = {}
    for f in bleed:
        gi = caps[f]["settings"].get("gruntIdx")
        by_grunt.setdefault(gi, []).append(f)
    # ⚠ THE GUARD THAT CAN ACTUALLY FIRE.  AD5b's claim is "3 of 3 GRUNT positions", so a run that
    # silently graded two of them would compare against a headline it does not cover.  s129's
    # three-outcome rule applied where partiality is REAL: a missing GRUNT class is data that
    # existed and went missing, so it is a REFUSAL, not an exclusion.
    if len(by_grunt) != len(GRUNT_NAME):
        die("AE3", f"only {len(by_grunt)} of {len(GRUNT_NAME)} GRUNT positions survive the "
                   f"bleed-free selection ({sorted(by_grunt)}) -- AD5b's headline is '3 of 3', so "
                   "a partial set is a malformed membership and must not be graded against it")
    for gi, fs in sorted(by_grunt.items()):
        if not fs:
            die("AE3", f"GRUNT {GRUNT_NAME[gi]} resolved to zero captures -- "
                       "`empty-gate-must-fail`")

    print(f"  {'GRUNT':>6} {'sweep':>14} {'n':>3}   "
          f"{'--- MODEL ---':>26}   {'--- ND ---':>26}")
    print(f"  {'':>6} {'':>14} {'':>3}   {'f0 Hz':>9} {'prom':>7} {'n_int':>7}   "
          f"{'f0 Hz':>9} {'prom':>7} {'n_int':>7}")
    per = {}
    for gi in sorted(by_grunt):
        for sw in DRIVEN:
            mp, mi, mf, pp, pi, pf = [], [], [], [], [], []
            for f in by_grunt[gi]:
                mv = rows[f]["model"][sw][FEATURE]["wide"]
                pv = rows[f]["pedal"][sw][FEATURE]["wide"]
                mp.append(mv["prom"]); mi.append(mv["n_interior"]); mf.append(mv["f0"])
                pp.append(pv["prom"]); pi.append(pv["n_interior"]); pf.append(pv["f0"])
            if not mp:
                continue
            # ⚠ An all-NaN centre column is MEANINGFUL here (no extremum -> no centre), so it is
            # handled explicitly rather than left to `np.nanmedian` to warn about.  s106's N3:
            # never let a non-finite reach a comparison silently -- test for it first.
            def med_f0(v):
                ok = [x for x in v if np.isfinite(x)]
                return float(np.median(ok)) if ok else float("nan")

            row = {"grunt": GRUNT_NAME[gi], "sweep": sw, "n": len(mp),
                   "model_prom": float(np.median(mp)), "model_nint": int(np.median(mi)),
                   "model_f0": med_f0(mf),
                   "nd_prom": float(np.median(pp)), "nd_nint": int(np.median(pi)),
                   "nd_f0": med_f0(pf)}
            per.setdefault(gi, []).append(row)
            mf0 = "     none" if not np.isfinite(row["model_f0"]) else f"{row['model_f0']:9.1f}"
            pf0 = "     none" if not np.isfinite(row["nd_f0"]) else f"{row['nd_f0']:9.1f}"
            print(f"  {GRUNT_NAME[gi]:>6} {sw:>14} {len(mp):3d}   "
                  f"{mf0} {row['model_prom']:7.2f} {row['model_nint']:7d}   "
                  f"{pf0} {row['nd_prom']:7.2f} {row['nd_nint']:7d}")

    # -- the dose-response, per side, per GRUNT.  A designed monotone axis is a free validity
    #    check on both sides (s109) and it is also AD5b's own claim.
    print(f"\n  DEPTH vs DRIVE -- span and monotonicity across the {len(DRIVEN)}-rung driven ladder")
    print(f"  {'GRUNT':>6}   {'ND span':>22}   {'model span':>22}")

    def fmt(v):
        mono = ("falling" if all(b < a for a, b in zip(v, v[1:]))
                else "rising" if all(b > a for a, b in zip(v, v[1:])) else "non-mono")
        return f"{max(v)-min(v):6.2f} dB {mono:>9}"

    frozen = 0
    spans = {}
    for gi in sorted(per):
        rr = per[gi]
        # ⚠ STRUCTURAL INVARIANT, NOT A TESTED GUARD, AND THE DIFFERENCE IS WORTH SAYING.  The
        # four sweeps are TIME WINDOWS of one capture file (`analyze.seg_of` indexes a fixed
        # table), not optional keys, so every row yields every rung by construction and this
        # branch cannot fire today.  It is kept as a cheap invariant against a future refactor
        # that makes sweeps optional -- and it is NOT claimed as a guard, because a guard that
        # cannot fire is worse than no guard.  The partiality that IS real here is a missing
        # GRUNT class, guarded above, and that is where s129's three-outcome rule lands.
        if len(rr) < len(DRIVEN):
            print(f"  {GRUNT_NAME[gi]:>6}   PARTIAL ({len(rr)}/{len(DRIVEN)} rungs) -- refusing "
                  f"to quote a span over an incomplete ladder")
            die("AE3", f"GRUNT {GRUNT_NAME[gi]} has {len(rr)} of {len(DRIVEN)} driven rungs.  "
                       "That is a MALFORMED read, not a physics outcome -- data that existed and "
                       "went missing (s129's three-outcome rule); refusing rather than excluding.")
        mv = [r["model_prom"] for r in rr]
        rv = [r["nd_prom"] for r in rr]
        spans[GRUNT_NAME[gi]] = {"model": mv, "nd": rv}
        if max(mv) - min(mv) < 0.1:
            frozen += 1
        print(f"  {GRUNT_NAME[gi]:>6}   {fmt(rv):>22}   {fmt(mv):>22}")

    # -- the threshold-free statement
    allm = [r for rr in per.values() for r in rr]
    zero_int = sum(1 for r in allm if r["model_nint"] == 0)
    faint = sum(1 for r in allm if r["model_prom"] < MIN_PROM_DB)
    nd_faint = sum(1 for r in allm if r["nd_prom"] < MIN_PROM_DB)
    print(f"\n  THRESHOLD-FREE:  cells where the MODEL's window contains NO interior extremum at "
          f"all: {zero_int} of {len(allm)}")
    print(f"  at GATE W's own {MIN_PROM_DB:.1f} dB bar: model faint in {faint} of {len(allm)}, "
          f"ND faint in {nd_faint} of {len(allm)}")
    counts = [(b, sum(1 for r in allm if r["model_prom"] < b)) for b in PROM_SWEEP]
    print(f"  bar sweep (model): " + "  ".join(f"<{b:.1f}dB:{c}" for b, c in counts))
    # ⚠ s106's N5 says a robustness sweep whose knob never turns is a constant printed N times.
    # That is TRUE HERE AND IT IS NOT A DEFECT, and the two cases must be told apart rather than
    # printing the same warning for both: a sweep is vacuous when the bar sits nowhere near the
    # data, and it is INFORMATIVE when the quantity is IDENTICALLY ZERO -- then no bar can ever
    # bind, and that is the result rather than a broken knob.  Distinguished by measurement.
    if len({c for _, c in counts}) == 1:
        if all(r["model_prom"] == 0.0 for r in allm):
            print(f"  -> the bar cannot bind at ANY setting because the model's prominence is "
                  f"IDENTICALLY 0.00 dB in every cell.  That constancy IS the finding (there is")
            print(f"     no extremum for a bar to grade), not a knob that failed to turn.")
        else:
            print(f"  ⚠ the bar excludes the SAME count at every setting while the quantity is "
                  f"NOT identically zero -- the knob is not turning, so this sweep is a constant "
                  f"printed {len(counts)} times (s106 N5) and says nothing about robustness.")
    out["ae3"] = {"per_grunt": {GRUNT_NAME[k]: v for k, v in per.items()}, "spans": spans,
                  "frozen_grunts": frozen, "model_zero_interior": zero_int,
                  "n_cells": len(allm), "model_faint": faint, "nd_faint": nd_faint,
                  "bar_sweep": [[b, c] for b, c in counts]}
    return per, frozen, zero_int, len(allm)


# =============================================================================================
# AE4  THE MIX BRANCH -- the discriminator
# =============================================================================================
def gate_ae4(rows, lad, out, resolution):
    """Does the feature exist where a MIX cancellation CAN exist?

    This is the sub-gate the session was built around.  s126: an `UNRESOLVED` on the bleed-free
    endpoints can be a MEMBERSHIP property rather than a physical one, because a cancellation has
    no bleed-free reading BY PHYSICS.  GATE W's stored w7 already classifies this feature
    "(b) MIX / BALANCE ... the feature VANISHES bleed-free" -- which, if it reproduces here, means
    AD5b measured the model in the one condition where its feature cannot appear."""
    print("\n" + "=" * 94)
    print("AE4  THE MIX BRANCH -- the same feature on the LEVEL ladder, where a mix EXISTS")
    print("=" * 94)
    print("  LEVEL is downstream of every filter, so a NETWORK corner cannot move with it and a")
    print("  MIX cancellation must -- and at LEVEL max the clean coefficient is exactly zero, so a")
    print("  cancellation VANISHES.  Read at the quietest stimulus, GATE W4's own condition, so")
    print("  drive is as far out of the picture as the capture set allows.")
    bar = max(W.MIX_MOVE_FRAC, 3.0 * resolution)
    print(f"  MIX bar: centre must move > {bar*100:.1f} % across the ladder "
          f"(3x the locator's measured {resolution*100:.2f} %, floored at "
          f"{W.MIX_MOVE_FRAC*100:.0f} %) -- GATE W4's own bar, imported")
    levels = sorted(lad)
    sw = SWEEPS[0]

    # ⚠⚠ THE MUTE IS MEASURED, NOT ASSUMED, AND THE FIRST DRAFT OF THIS SUB-GATE LET IT IN.
    # At LEVEL min the MODEL mutes (GATE L7 -- `divRatio(0)` is exactly 0 and the shipped stage
    # pins the wiper on VD), so that render is numerical noise: the estimator duly found **68**
    # interior extrema in it and its meaningless argmin was dragging the model's LEVEL span to
    # 44.8 %, i.e. straight past the MIX bar, from a row that carries no signal at all.  GATE W2
    # excludes it and MEASURES the mute rather than expecting it, because "excluded because we
    # expect silence" is how a genuinely broken render gets waved through.  Same here.
    muted = {}
    for side in ("model", "pedal"):
        for lv in levels:
            pk = rows[lad[lv]][side][sw]["peak_db"]
            if pk < W.SILENT_DB:
                muted.setdefault(side, []).append((lv, pk))
    print(f"\n  MUTE CHECK (peak of the smoothed curve; bar {W.SILENT_DB:.0f} dB, GATE W's own):")
    for side in ("model", "pedal"):
        m = muted.get(side, [])
        print(f"      {side:<6s} silent at {len(m)} detent(s)" +
              ("" if not m else "  " + ", ".join(f"LEVEL {lv:.3f} ({pk:.0f} dB)" for lv, pk in m)))
    if "model" not in muted:
        die("AE4", f"the MODEL is NOT silent at any LEVEL detent -- GATE L7 says it mutes at "
                   f"LEVEL min, so either that has changed or this is reading the wrong rows.  "
                   f"An exclusion whose premise no longer holds must be re-derived, not applied.")

    res = {}
    for side in ("model", "pedal"):
        dead = {lv for lv, _ in muted.get(side, [])}
        print(f"\n  {side.upper():<6s}  " + " ".join(f"{lv:>8.3f}" for lv in levels))
        f0s, proms, nints = [], [], []
        for lv in levels:
            v = rows[lad[lv]][side][sw][FEATURE]["wide"]
            f0s.append(v["f0"]); proms.append(v["prom"]); nints.append(v["n_interior"])
        print(f"    f0 Hz  " + " ".join("     nan" if not np.isfinite(x) else f"{x:8.1f}"
                                        for x in f0s))
        print(f"    prom   " + " ".join(f"{x:8.2f}" for x in proms))
        print(f"    n_int  " + " ".join(f"{x:8d}" for x in nints))
        if dead:
            print(f"    (MUTED, excluded from the span and the presence count: " +
                  ", ".join(f"LEVEL {lv:.3f}" for lv in sorted(dead)) + ")")
        live = [i for i, lv in enumerate(levels) if lv not in dead]
        ok = [f0s[i] for i in live if np.isfinite(f0s[i])]
        span = (max(ok) / min(ok) - 1.0) if len(ok) >= 3 else float("nan")
        # PRESENT anywhere on the ladder?  This is the H1-vs-H2 discriminator and it needs no bar
        # beyond GATE W's own faintness bar.
        present = [i for i in live if nints[i] > 0 and proms[i] >= MIN_PROM_DB]
        verdict = ("UNRESOLVED" if not np.isfinite(span)
                   else "MIX" if span > bar else "NETWORK")
        res[side] = {"levels": levels, "f0": f0s, "prom": proms, "n_interior": nints,
                     "span_frac": span, "verdict": verdict, "n_live": len(live),
                     "muted_levels": sorted(dead),
                     "present_detents": [levels[i] for i in present]}
        print(f"    -> span {'nan' if not np.isfinite(span) else f'{span*100:.1f} %'}"
              f"   verdict {verdict}"
              f"   present (n_int>0 AND prom>={MIN_PROM_DB:.1f} dB) at "
              f"{len(present)}/{len(live)} live detents")
    # ⚠⚠ THE TWO SPANS ABOVE ARE OVER DIFFERENT DETENT SETS AND MUST NOT BE COMPARED.  The model
    # is MUTED at LEVEL min and loses the feature above LEVEL noon; ND keeps it almost to the top.
    # So "model 9.1 % vs ND 133.5 %" is a membership difference wearing a physics number -- the
    # exact trap `aggregate-moved-check-membership-first` names, and s116's rule that a matched
    # design is worth more than a fitted correction.  The only quotable comparison is over the
    # detents where BOTH sides resolve the feature.
    common = [i for i, lv in enumerate(levels)
              if all(np.isfinite(res[s]["f0"][i]) and res[s]["n_interior"][i] > 0
                     and lv not in set(res[s]["muted_levels"]) for s in ("model", "pedal"))]
    print(f"\n  MATCHED-DETENT LEVEL SENSITIVITY -- the only comparable statement here")
    if len(common) < 3:
        print(f"    only {len(common)} detent(s) resolve on BOTH sides; refusing to quote a ratio "
              f"over fewer than 3 (a span needs an axis, not two points).")
        out["ae4"] = dict(res, matched=None)
        return res
    lvs = [levels[i] for i in common]
    sp = {}
    for side in ("model", "pedal"):
        v = [res[side]["f0"][i] for i in common]
        sp[side] = max(v) / min(v) - 1.0
        print(f"    {side:<6s} LEVEL {lvs[0]:.3f}..{lvs[-1]:.3f}: "
              f"{min(v):7.1f} -> {max(v):7.1f} Hz   span {sp[side]*100:5.1f} %")
    ratio = sp["pedal"] / sp["model"] if sp["model"] > 0 else float("inf")
    print(f"    ⇒ ND's centre is {ratio:.1f}x more LEVEL-sensitive than ours over the SAME "
          f"{len(common)} detents.")
    print(f"      Two mixers summing the same two paths must respond to LEVEL the same way, so a")
    print(f"      difference this size is a measurement on open work item 9 (GATE L4's "
          f"(a) structural vs (b) level-dependent-downstream), on a SECOND feature -- s125")
    print(f"      already flagged the bass notch at ~2x on this same ladder.  Reported, not "
          f"resolved: this gate does not discriminate L4(a) from L4(b).")
    out["ae4"] = dict(res, matched={"levels": lvs, "span_frac": sp, "ratio": ratio})
    return res


# =============================================================================================
# AE5  THE COMPUTED VERDICT
# =============================================================================================
def gate_ae5(ae3, ae4, out):
    """Every branch below is derived from the numbers above.  Deleting the data must change the
    verdict, not merely the table under it -- `computed-verdicts-not-narrated`, and the two
    COMPUTED-VERDICT arms of this gate's mutation runner test exactly that."""
    per, frozen, zero_int, n_cells = ae3
    print("\n" + "=" * 94)
    print("AE5  VERDICT")
    print("=" * 94)

    m_present_bf = n_cells - zero_int
    m_lad = ae4["model"]
    p_lad = ae4["pedal"]
    m_on_ladder = len(m_lad["present_detents"])
    p_on_ladder = len(p_lad["present_detents"])

    # ND's own behaviour, so the model's is quoted against something rather than in isolation.
    nd_rising = sum(1 for g in per.values()
                    if all(b > a for a, b in zip([r["nd_prom"] for r in g],
                                                 [r["nd_prom"] for r in g][1:])))
    print(f"  bleed-free   MODEL has an interior extremum in {m_present_bf} of {n_cells} cells; "
          f"depth FROZEN (span < 0.1 dB) in {frozen} of {len(per)} GRUNT positions")
    print(f"               ND's depth rises monotonically with drive in {nd_rising} of "
          f"{len(per)} GRUNT positions")
    print(f"  LEVEL ladder MODEL present at {m_on_ladder} of {len(m_lad['levels'])} detents "
          f"(verdict {m_lad['verdict']}); ND at {p_on_ladder} (verdict {p_lad['verdict']})")
    print()

    # ND's own bleed-free presence is the OTHER half of the verdict and the first draft of this
    # sub-gate did not use it -- it branched on the model alone, which cannot distinguish "we are
    # missing something they have" from "neither side has anything here".
    nd_present_bf = sum(1 for g in per.values() for r in g
                        if r["nd_nint"] > 0 and r["nd_prom"] >= MIN_PROM_DB)
    print(f"               ND has an interior extremum over the "
          f"{MIN_PROM_DB:.1f} dB bar in {nd_present_bf} of {n_cells} cells")

    if m_present_bf == 0 and nd_present_bf > 0:
        # The load-bearing case.  Note what is CONFIRMED and what needs a qualifier -- AD5b's
        # bleed-free reading is not merely reproduced here, it is STRENGTHENED (0.69 dB of
        # coarse-grid prominence becomes "no extremum exists at all"), and only its unconditional
        # WORDING needs correcting.
        if m_on_ladder > 0:
            verdict = ("CONFIRMED bleed-free, WITH A QUALIFIER -- the model lacks a "
                       "DRIVE-GENERATED feature, not every feature")
            why = (f"AD5b's bleed-free reading is CONFIRMED and strengthened: on a grid 18x finer "
                   f"the model's window contains NO interior extremum at all in {n_cells} of "
                   f"{n_cells} cells, so its 0.69 dB was an inflection and there is nothing there "
                   f"to grade -- a statement with no threshold in it.  ND has one in "
                   f"{nd_present_bf} of {n_cells}, deepening monotonically with drive in "
                   f"{nd_rising} of {len(per)} GRUNT positions.  BUT the unconditional wording "
                   f"'we appear to have no null there at all' needs ONE qualifier: the model is "
                   f"not featureless in this region -- it carries a MIX cancellation, present at "
                   f"{m_on_ladder} LEVEL detents and vanishing as the clean tap does, which is "
                   f"exactly the membership situation s126 found for the bass peak.  ⇒ what we "
                   f"are missing is ND's DRIVE-GENERATED null, and the two sides' features here "
                   f"are not the same KIND of object: ours is a balance, theirs is a balance PLUS "
                   f"something the OD path generates.  That is open work item 6's signature, at "
                   f"the top of the band, and it is a presence/absence question rather than a "
                   f"centre or a depth.")
        else:
            verdict = "MISSING FEATURE -- outright"
            why = (f"the model has NO interior extremum in this window under ANY condition "
                   f"measured, bleed-free or mixed, while ND has one in {nd_present_bf} of "
                   f"{n_cells} bleed-free cells.  Nothing here is a mis-tuned centre or a shallow "
                   f"depth; there is no feature to tune.")
    elif m_present_bf == 0 and nd_present_bf == 0:
        verdict = "NEITHER SIDE HAS ONE bleed-free"
        why = ("no bleed-free cell on either side carries an interior extremum over the bar, so "
               "there is no model/reference difference here to own.  AD5b's asymmetry does not "
               "survive the finer grid, and this feature should come off item 6's list.")
    elif frozen == len(per) and m_present_bf > 0:
        verdict = "PRESENT BUT PINNED"
        why = ("the model does have an interior extremum bleed-free, but its depth does not move "
               "with drive while ND's does.  That is item 6's DEPTH axis (AD5's bridged-T row), "
               "not a presence/absence question -- a candidate must COMPRESS a notch's depth with "
               "drive, and this is a second sized instance of that.")
    else:
        verdict = "MIXED -- read the table"
        why = ("the model's readings are neither uniformly absent nor uniformly frozen.  No "
               "single statement covers the conditions; quote the cell, not the pool.")

    print(f"  ⇒ {verdict}")
    for line in _wrap(why, 88):
        print(f"    {line}")
    print()
    print("  ⛔ NOT CLAIMED: anything about hardware.  `reference-sources.md` §1 gives this")
    print("     feature to NEITHER reference, and §3's driven charts disagree between conditions.")
    print("     Nothing above is evidence that a real B7K does either thing.")
    print("  ⛔ NOT CLAIMED: a mechanism.  ND is a black box; the LEVEL and drive dose-responses")
    print("     are signatures, and this gate reports what they are consistent with.")
    out["ae5"] = {"verdict": verdict, "why": why, "model_present_bleed_free": m_present_bf,
                  "nd_present_bleed_free": nd_present_bf,
                  "n_cells": n_cells, "frozen_grunts": frozen, "n_grunts": len(per),
                  "nd_rising_grunts": nd_rising,
                  "model_present_detents": m_on_ladder, "nd_present_detents": p_on_ladder}
    return verdict


def _wrap(s, n):
    words, line, out = s.split(), "", []
    for w in words:
        if len(line) + len(w) + 1 > n:
            out.append(line)
            line = w
        else:
            line = (line + " " + w).strip()
    if line:
        out.append(line)
    return out


# =============================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("report", nargs="?", default=REPORT)
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--jobs", type=int, default=None)
    a = ap.parse_args()

    rep = AD.Report(a.report)
    out = {"report": a.report, "feature": FEATURE, "window_hz": list(WINDOW),
           "grid_frac": W.GRID_FRAC}

    caps, bleed, lad, ad_groups, files = gate_ae0(rep)
    resolution = gate_ae1a(out, a.jobs)
    print(f"\n  rendering {len(files)} captures into {REN_DIR} ...")
    rows = collect(files, a.jobs)
    missing = [f for f in files if f not in rows]
    if missing:
        die("AE0", f"{len(missing)} capture(s) produced no row: {missing[:3]} -- a PARTIAL "
                   "collection is a malformed run, not an exclusion (s129)")
    gate_ae1b(rows, bleed, out)
    gate_ae1c(rep, ad_groups, rows, out)
    gate_ae2(rows, bleed, lad, out)
    ae3 = gate_ae3(rows, bleed, caps, out)
    ae4 = gate_ae4(rows, lad, out, resolution)
    gate_ae5(ae3, ae4, out)

    os.makedirs(os.path.dirname(a.out), exist_ok=True)
    with open(a.out, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {a.out}")


if __name__ == "__main__":
    main()
