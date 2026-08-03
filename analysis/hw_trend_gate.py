#!/usr/bin/env python3.11
"""GATE AD -- are we drifting AWAY from the hardware, while the release gate says we improve?
Session 130.

WHY THIS EXISTS
---------------
`reference-sources.md` §1 splits authority between two references: the ND captures (linear/EQ,
absolute level) and the HARDWARE charts (broadband tilt, OD-path low-mids, ~320 Hz null depth,
harmonic structure).  §5 rule 2 then says, in as many words:

    "A candidate that moves away from the captures toward a documented hardware trend is a PASS,
     not a regression."

⚠⚠ NOTHING ENFORCES THAT.  `analysis/release_gate.py` is 100 % ND-referenced -- its single mention
of hardware is a COMMENT explaining that `c21R` deliberately departs from ND.  So the project's
one mechanical arbiter cannot distinguish "moved toward ND" from "moved away from hardware", and
the doctrine that tells them apart lives only in a rules file a session has to remember to apply.
That is exactly the failure mode s125 found three times in one session (a distinction flattened in
a summary and then acted on).  This gate is the guard: it reads the shipped baseline and reports,
per hardware trend, WHICH WAY WE ARE LEANING.

⛔⛔ WHAT THIS GATE IS NOT.  It is NOT a fit target and must never become one.  §5 rule 3:

    "Do not fit to §3 or §4 numbers directly.  They are chart reads with unknown exact conditions.
     Use them to set the SIGN and the ORDER OF MAGNITUDE of a target."

So every graded verdict below is a SIGN or an ORDERING.  No bar anywhere in this file is derived
from a hardware number, and the two places a bar IS needed take it from a quantity this project
measured independently (AD1's route bar from GATE O's route gap).  The "% of the way" columns are
PRINTED so the size stays quotable and are GRADED NOWHERE.

WHAT IT MEASURES.  Absolute, NOT gain-matched: raw model = `plugin_db - gain_db_applied`
(s116 GATE U2 -- `plugin_db` carries a null gain fitted against that row's PEDAL capture, so it is
not the model's own number).  Three trends, from `reference-sources.md`:

  T1  §2  clean-path broadband tilt.  HW carries a gentle mid-emphasis re ND, hinged ~65 Hz and
          ~2.7 kHz; -1.1 dB at 20 Hz, +0.32 at 800 Hz-1 kHz, -1.1 at 16 kHz.  §2 is the only
          section the file considers "precise enough to fit against" (two hardware units, 4 dB
          window, gridlines) -- and `c21R` 220k->130k was already shipped against its LF end.
  T2  §3  OD-path 150-250 Hz.  HW is +2.8..+4.8 dB above ND in every DRIVEN condition and
          EXACTLY 0 dB at GRUNT cut and on the clean sweep.
  T3  §3  ~320 Hz cancellation null.  HW deeper than ND in all six charted conditions.

MEASURED, SESSION 130 (the headline -- run the gate for live numbers, do not transcribe):

  T1  6 of 8 graded bands lean HARDWARE.  Both hinges reproduce.  The ONE inversion is the
      800 Hz-1 kHz mid-emphasis: HW sits +0.32 dB ABOVE ND and we sit ~0.21-0.27 BELOW it, so we
      are ~0.5-0.6 dB the wrong side.  Small, and NEW -- no work item names it.
  T2  Every cell is NEGATIVE (the model is 3.6-7.8 dB below ND at 160-254 Hz -- that is A3), so
      the model->HW gap is 5-9 dB and points the SAME WAY at every GRUNT position, quantifying
      §3's "the two corrections compound, they do not fight".
      ⭐ BUT SPLIT IT AND THE TWO HALVES DISAGREE.  The LEVEL-INVARIANT half -- the GRUNT contrast
      (boost-cut), immune to any absolute-level error -- has the SAME SIGN as hardware's and a
      comparable size (ours +1.2..+4.2 dB wider than ND's, hardware's +2.8..+4.8).  ⇒ the GRUNT
      SPAN is already leaning hardware; the whole 5-9 dB is the absolute PEDESTAL, i.e. A3.
  T3  5 of 6 conditions order HW > ND > model as expected.  One inverts (GRUNT cut @ drv_-18,
      n=11, model 2.13 dB DEEPER than ND).

GATES.  Hard exits cover this gate's OWN validity only; every physics outcome is a computed
verdict and execution continues (s108's rule).
--------------------------------------------------------------------------------------------
AD1  KNOWN ANSWER -- ROUTE INVARIANCE.  The clean tilt is measured on TWO independent capture
     routes (DIST disengaged, and BLEND=0).  They differ by a ~2.2 dB absolute route offset and
     must agree on SHAPE.  Bar taken from an independently measured quantity, never guessed:
     GATE O's route/session gap, 0.30 dB (s107, `reference-sources.md` §1a).  Measured 0.148.
     ⚠ This is what makes T1's 0.5 dB inversion readable at all -- without it, 0.5 dB is
     indistinguishable from a route artefact.
AD2  MEMBERSHIP, asserted, never inferred.  Report NAMED and refused if it predates s118 or was
     rendered with `--fit` overrides (it is then not the shipped model).  Every group's count
     printed; every required band must exist on the report's own grid; an empty group is a hard
     exit, and a PARTIAL group is a REFUSAL, not a silent exclusion (s129's three-outcome rule).
AD3  T1 -- clean tilt SIGN per band.  Verdict per band: LEANS HW / LEANS ND / (crossover).
     ⚠ The LF bands are a FRAME PIN, not evidence: `c21R` was fitted to this very anchor (s91), so
     they are guaranteed to pass and are labelled as such (s119's rule -- a term the model was
     fitted to cannot certify the model).  The MID and HF bands are the load-bearing ones.
AD4  T2 -- OD low-mid, split into the two halves above.  The absolute pedestal is REPORTED with
     its level-error caveat; the GRUNT contrast is GRADED on sign, because it is the half that
     survives a common-mode level error.
AD5  T3 -- 320 Hz null depth ORDERING (model vs ND).  ⚠⚠ The depth here is a 3-band prominence on
     the report's ~1/3-octave grid and is a LOWER BOUND ONLY -- `measurement-discipline.md` is
     explicit that this grid understated one notch by 20 dB.  Graded on ORDERING, never on value;
     for a real depth use `analysis/null_locus_gate.py` (GATE R, 1/6-oct power-integrated).
AD6  DIRECTION OF TRAVEL.  One line per trend: toward hardware, away from both, or mixed.  This is
     the statement the release gate structurally cannot make.

Run:  /opt/homebrew/bin/python3.11 analysis/hw_trend_gate.py
      /opt/homebrew/bin/python3.11 analysis/hw_trend_gate.py --report analysis/reports/X.json
"""
import argparse
import json
import os
import sys

import numpy as np

DEFAULT_REPORT = "analysis/reports/s124_ship.json"

# ---------------------------------------------------------------------------------------------
# The HARDWARE side.  PNG READS from `reference-sources.md` §2/§3 -- SIGN and ORDER OF MAGNITUDE
# ONLY (§5 rule 3).  Nothing in this file may fit to them or derive a threshold from them.
# ---------------------------------------------------------------------------------------------
# §2, HW - ND, clean flat-EQ.  Keyed by the report band nearest the chart's own anchor frequency.
# 0.0 marks a CROSSOVER (the chart's two traces meet) -- reported, never sign-graded.
HW_TILT_DB = {
    20.0: -1.10,      # chart 20 Hz
    31.7: -0.75,      # chart 30 Hz
    63.5: 0.00,       # chart ~65 Hz  CROSSOVER
    201.6: 0.00,      # chart 200 Hz  -- the tilt REFERENCE band (see TILT_REF_HZ)
    806.3: +0.32,     # chart 800 Hz
    1015.9: +0.32,    # chart 1 kHz
    2560.0: 0.00,     # chart ~2.7 kHz  CROSSOVER
    5120.0: -0.39,    # chart 5 kHz
    10240.0: -0.81,   # chart 10 kHz
    16255.0: -1.10,   # chart 16 kHz
}
# Reference the tilt where the PUBLISHED comparison reads zero -- `retarget-against-model-not-
# reference` (s91) prescribes exactly this, so the model's curve and the chart's share an origin
# that is not itself in dispute.
TILT_REF_HZ = 201.6

# §3, HW - ND over 150-250 Hz, driven conditions.  A RANGE, deliberately: it is a chart read.
HW_LOWMID_DRIVEN_DB = (+2.8, +4.8)
HW_LOWMID_CUT_DB = 0.0        # §3: "exactly 0 dB at GRUNT cut / on the clean sweep"
# §3: HW's ~320 Hz null is deeper than ND's in ALL SIX charted conditions.
HW_NULL_DEEPER_THAN_ND = True

LOWMID_HZ = (160.0, 201.6, 254.0)      # the report bands inside §3's 150-250 Hz window

# The 250-800 Hz FEATURE TRAIN, as (name, (lo, centre, hi), kind, hardware-statement-exists).
# Only the first has a published hardware result; the other two are measured against ND and
# reported, because §2's clean anchors jump 200 -> 800 Hz and would otherwise skip this region
# entirely.  Inventing a hardware value for the other two would be fitting to a chart (§5 rule 3).
FEATURE_TRAIN = (
    ("320 Hz null",    (254.0, 320.0, 403.2),   "notch", True),
    ("recovery peak",  (320.0, 403.2, 640.0),   "peak",  False),
    ("bridged-T dip",  (508.0, 640.0, 1015.9),  "notch", False),
)
# ⚠ The bridged-T notch is at ~700-716 Hz (circuit.md's recovery network; GATE W measures the
# model's at 715.8-716.9 and the pedal's at 695.7-745.4).  That falls BETWEEN this report's 640.0
# and 806.3 Hz bands, so NO band sits at its bottom and the read below is weaker than the other
# two -- it is a presence/ordering indicator only.  GATE W is the instrument for that feature.
NULL_HZ = tuple(sorted({f for _, tri, _, _ in FEATURE_TRAIN for f in tri}))

# §3's "5-6 kHz null" row.  §1's authority column for it reads "Neither -- unresolved".  It is
# absent from the clean sweep (⇒ drive-dependent) and the driven charts disagree between
# conditions, so AD5b measures it and grades NOTHING against hardware.  Window edges only -- the
# centre is located per condition, because the feature moves.
HF_NULL_WINDOW = (4063.7, 8127.5)
GRUNT_NAME = {0: "boost", 1: "cut", 2: "flat"}
SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
DRIVEN = SWEEPS[1:]

# AD1's bar.  NOT guessed: GATE O (s107) measured the capture-route and capture-session terms at
# 0.17-0.23 dB each; 0.30 dB is their ceiling.  See `reference-sources.md` §1a, s107 entry.
ROUTE_BAR_DB = 0.30

# AD2.  The absolute ledgers were re-based by session 115's shipped constants; GATE O refuses
# anything earlier BY NAME and so does this gate (`rebaseline-all-derived-artefacts`, s118).
MIN_BASELINE_SESSION = 118


def die(tag, msg):
    print(f"\n[{tag}] REFUSED: {msg}")
    sys.exit(1)


def flat_eq(s):
    return all(abs(s.get(k, 0.5) - 0.5) < 1e-9 for k in ("lo", "loMid", "hiMid", "hi"))


def bleed_free(s):
    # GATE K2 (s103): the clean tap vanishes only where BOTH BLEND and LEVEL are max.
    return s.get("blend") == 1.0 and s.get("level") == 1.0


class Report:
    def __init__(self, path):
        self.path = path
        with open(path) as fh:
            self.d = json.load(fh)
        self.bands = np.array(self.d["meta"]["bands"], dtype=float)
        self.captures = self.d["captures"]

    def idx(self, f):
        i = int(np.argmin(np.abs(self.bands - f)))
        if abs(self.bands[i] - f) > 1e-6:
            die("AD2", f"band {f} Hz is not on this report's grid (nearest {self.bands[i]}). "
                       "The band list changed; re-derive this gate's anchors, do not re-point them.")
        return i

    def select(self, pred):
        return [c for c in self.captures if pred(c.get("settings", {}))]

    def delta(self, c, sweep):
        """absolute (model - ND) per band, dB.  None when the sweep is absent."""
        fr = c.get("fr", {}).get(sweep)
        if not fr:
            return None
        p = np.array(fr["plugin_db"], dtype=float) - float(fr["gain_db_applied"])
        return p - np.array(fr["pedal_db"], dtype=float)

    def raw(self, c, sweep):
        """(model_db, nd_db) absolute, per band.  None when the sweep is absent."""
        fr = c.get("fr", {}).get(sweep)
        if not fr:
            return None
        p = np.array(fr["plugin_db"], dtype=float) - float(fr["gain_db_applied"])
        return p, np.array(fr["pedal_db"], dtype=float)


# =============================================================================================
# AD2  MEMBERSHIP
# =============================================================================================
def gate_membership(rep):
    print("=" * 94)
    print("AD2  MEMBERSHIP -- asserted, not inferred")
    print("=" * 94)

    name = os.path.basename(rep.path)
    print(f"  report            {name}")
    meta = rep.d.get("meta", {})

    overrides = meta.get("fit_overrides") or []
    if overrides:
        die("AD2", f"report was rendered with --fit {overrides}; that is not the shipped model, "
                   "so a hardware-lean verdict from it says nothing about what we ship.")

    digits = "".join(ch for ch in name.split("_")[0] if ch.isdigit())
    if digits and int(digits) < MIN_BASELINE_SESSION:
        die("AD2", f"{name} predates session {MIN_BASELINE_SESSION}.  Every statistic here is "
                   "ABSOLUTE (not gain-matched), and session 115's shipped kOutputMakeup/PWL taper "
                   "moved the absolute frame by -3.90 dB.  Re-render before comparing.")
    print(f"  fit overrides     none (shipped constants)")
    print(f"  bands             {len(rep.bands)}  ({rep.bands[0]:.1f} .. {rep.bands[-1]:.1f} Hz)")

    for f in set(HW_TILT_DB) | set(LOWMID_HZ) | set(NULL_HZ):
        rep.idx(f)                     # raises via die() if the grid moved
    print(f"  required bands    all present")

    groups = {
        "clean / DIST disengaged": rep.select(lambda s: s.get("distEngage") is False and flat_eq(s)),
        "clean / BLEND=0": rep.select(lambda s: s.get("blend") == 0.0 and flat_eq(s)),
    }
    for gi in (0, 1, 2):
        groups[f"OD bleed-free / GRUNT {GRUNT_NAME[gi]}"] = rep.select(
            lambda s, gi=gi: s.get("gruntIdx") == gi and bleed_free(s)
            and s.get("distEngage") is True and flat_eq(s))

    for label, g in groups.items():
        print(f"  {label:34s} n={len(g):3d}")
        if not g:
            die("AD2", f"group '{label}' is EMPTY.  A gate with no data must fail, not fall "
                       "through to its else-branch.")

    # s129's three-outcome rule: "never had data" and "lost data" must not share a branch.
    for label, g in groups.items():
        if label.startswith("OD"):
            have = [len([1 for sw in DRIVEN if c["fr"].get(sw)]) for c in g]
            partial = [n for n in have if 0 < n < len(DRIVEN)]
            if partial:
                die("AD2", f"group '{label}' has {len(partial)} capture(s) carrying SOME but not "
                           f"all of {list(DRIVEN)}.  That is a malformed report (data that existed "
                           "and went missing), not a physics outcome -- refusing rather than "
                           "silently excluding.")
    print("  partial-sweep check                PASS (every OD capture is complete or absent)")
    return groups


# =============================================================================================
# AD1  KNOWN ANSWER -- route invariance of the clean tilt
# =============================================================================================
def tilt(rep, group, sweep="sweep_clean"):
    """median (model - ND) per band, re-referenced to TILT_REF_HZ."""
    rows = [v for c in group if (v := rep.delta(c, sweep)) is not None]
    if not rows:
        return None
    med = np.nanmedian(np.array(rows), axis=0)
    return med - med[rep.idx(TILT_REF_HZ)], len(rows)


def gate_route(rep, groups):
    print()
    print("=" * 94)
    print("AD1  KNOWN ANSWER -- the clean tilt must be ROUTE-INVARIANT")
    print("=" * 94)
    a = tilt(rep, groups["clean / DIST disengaged"])
    b = tilt(rep, groups["clean / BLEND=0"])
    if a is None or b is None:
        die("AD1", "a clean route produced no sweep_clean rows.")
    (ta, na), (tb, nb) = a, b
    sel = [rep.idx(f) for f in sorted(HW_TILT_DB)]
    worst = float(np.nanmax(np.abs(ta[sel] - tb[sel])))
    print(f"  route A  DIST disengaged   n={na}")
    print(f"  route B  BLEND=0           n={nb}")
    print(f"  bar                        {ROUTE_BAR_DB:.2f} dB  (GATE O's measured route/session "
          f"gap, s107 -- NOT a number chosen here)")
    print(f"  worst |A - B| over the graded bands   {worst:.3f} dB   "
          f"{'PASS' if worst <= ROUTE_BAR_DB else 'FAIL'}")
    if worst > ROUTE_BAR_DB:
        die("AD1", f"the two clean routes disagree on SHAPE by {worst:.3f} dB, above the "
                   f"independently measured {ROUTE_BAR_DB:.2f} dB route gap.  A 0.5 dB trend "
                   "verdict below would be unreadable against that; refusing.")
    print("  ⇒ the tilt statistic resolves ~0.15 dB, so AD3's sub-dB verdicts are readable.")
    return ta, tb


# =============================================================================================
# AD3  T1 -- clean-path tilt, sign per band
# =============================================================================================
def gate_tilt(rep, ta, tb):
    print()
    print("=" * 94)
    print("AD3  TREND 1 -- clean-path broadband tilt vs hardware (§2)")
    print("=" * 94)
    print(f"  all values re {TILT_REF_HZ} Hz, where the published HW-ND comparison reads zero")
    print()
    print("  EVERY band is printed.  §2's chart anchors are sparse -- it is a smooth 4 dB window")
    print("  read off a PNG -- but printing only the anchors would jump 200 -> 800 Hz and hide the")
    print("  250-800 Hz feature train (notch ~320, recovery peak ~400-500, dip ~640-800) wholesale.")
    print("  Bands with no §2 anchor are REPORTED and carry no verdict: inventing a hardware value")
    print("  for them would be exactly the fitting-to-a-chart that §5 rule 3 forbids.  Those")
    print("  features ARE gradeable -- on the DRIVEN charts, in AD5, not on this clean sweep.")
    print()
    print(f"  {'band':>9} {'HW-ND §2':>9} {'model-ND A':>11} {'model-ND B':>11} "
          f"{'% of HW':>8}  verdict")

    lean_hw = lean_nd = 0
    inversions = []
    for i, f in enumerate(rep.bands):
        f = float(f)
        ma, mb = float(ta[i]), float(tb[i])
        m = 0.5 * (ma + mb)
        if f not in HW_TILT_DB:
            print(f"  {f:9.1f} {'--':>9} {ma:+11.3f} {mb:+11.3f} {'':>8}  "
                  f"(no §2 anchor -- reported only)")
            continue
        hw = HW_TILT_DB[f]
        if abs(hw) < 1e-9:
            verdict = "(crossover -- reported, not graded)"
            pct = ""
        else:
            # PRINTED so the size stays quotable; GRADED NOWHERE (§5 rule 3).
            pct = f"{100.0 * m / hw:7.0f}%"
            if np.sign(m) == np.sign(hw):
                lean_hw += 1
                verdict = "LEANS HARDWARE"
            else:
                lean_nd += 1
                inversions.append((f, hw, m))
                verdict = "⚠ WRONG SIDE OF ND"
        # c21R (s91) was fitted to this anchor's LF end -- a term the model was fitted to cannot
        # certify the model (s119).  Say so at the row, not in a footnote.
        pin = "  [FRAME PIN: c21R fitted here]" if f <= 31.7 else ""
        print(f"  {f:9.1f} {hw:+9.2f} {ma:+11.3f} {mb:+11.3f} {pct:>8}  {verdict}{pin}")

    graded = lean_hw + lean_nd
    print()
    print(f"  VERDICT  {lean_hw} of {graded} graded bands lean HARDWARE, {lean_nd} lean ND.")
    for f, hw, m in inversions:
        print(f"           ⚠ {f:.1f} Hz: hardware is {hw:+.2f} dB re ND and we are {m:+.3f} -- "
              f"we are {abs(m - hw):.2f} dB the wrong side.")
    if not inversions:
        print("           No band sits on the wrong side of ND.")
    return lean_hw, lean_nd, inversions


# =============================================================================================
# AD4  T2 -- OD-path 150-250 Hz
# =============================================================================================
def gate_lowmid(rep, groups):
    print()
    print("=" * 94)
    print("AD4  TREND 2 -- OD-path 150-250 Hz vs hardware (§3)")
    print("=" * 94)
    lm = [rep.idx(f) for f in LOWMID_HZ]
    print(f"  bands {list(LOWMID_HZ)} Hz, bleed-free (BLEND=LEVEL=max), flat EQ")
    print(f"  §3: HW-ND = {HW_LOWMID_DRIVEN_DB[0]:+.1f}..{HW_LOWMID_DRIVEN_DB[1]:+.1f} dB driven, "
          f"{HW_LOWMID_CUT_DB:+.1f} at GRUNT cut / clean")
    print()

    ped = {}
    print("  (a) ABSOLUTE pedestal -- model - ND")
    print(f"      {'GRUNT':>6} {'sweep':>14} {'n':>3}  {'model-ND':>9}   implied model->HW gap")
    for gi in (0, 1, 2):
        g = groups[f"OD bleed-free / GRUNT {GRUNT_NAME[gi]}"]
        for sw in SWEEPS:
            rows = [v for c in g if (v := rep.delta(c, sw)) is not None]
            if not rows:
                continue
            v = float(np.nanmedian(np.array(rows)[:, lm]))
            ped[(gi, sw)] = v
            if gi == 1 or sw == "sweep_clean":
                gap = f"{HW_LOWMID_CUT_DB - v:+.1f} dB"
            else:
                gap = (f"{HW_LOWMID_DRIVEN_DB[0] - v:+.1f} .. "
                       f"{HW_LOWMID_DRIVEN_DB[1] - v:+.1f} dB")
            print(f"      {GRUNT_NAME[gi]:>6} {sw:>14} {len(rows):3d}  {v:+9.3f}   {gap}")
    print("      ⚠ ABSOLUTE, so a common-mode level error lands here in full.  REPORTED, not")
    print("        graded.  This half is A3 (`CLAUDE.md`: the OD path is ~4.4 dB quiet vs ND).")

    print()
    print("  (b) GRUNT CONTRAST -- level-INVARIANT, and therefore the half that is graded")
    print("      (model_X - model_cut) - (ND_X - ND_cut); any common-mode gain cancels exactly.")
    print(f"      §3's hardware contrast is {HW_LOWMID_DRIVEN_DB[0]:+.1f}..{HW_LOWMID_DRIVEN_DB[1]:+.1f} dB "
          f"(driven, re its own GRUNT cut = 0)")
    print()
    print(f"      {'GRUNT':>6} {'sweep':>14}  {'contrast':>9}  verdict")
    agree = disagree = 0
    for gi in (0, 2):
        for sw in DRIVEN:
            if (gi, sw) not in ped or (1, sw) not in ped:
                continue
            c = ped[(gi, sw)] - ped[(1, sw)]
            same = np.sign(c) == np.sign(HW_LOWMID_DRIVEN_DB[0])
            agree, disagree = (agree + 1, disagree) if same else (agree, disagree + 1)
            print(f"      {GRUNT_NAME[gi]:>6} {sw:>14}  {c:+9.3f}  "
                  f"{'SAME SIGN AS HARDWARE' if same else '⚠ OPPOSITE SIGN TO HARDWARE'}")
    print()
    print(f"  VERDICT  GRUNT contrast: {agree} of {agree + disagree} cells share hardware's sign.")
    if agree and not disagree:
        print("           ⇒ the SPAN half of §3's low-mid trend already leans hardware; what is")
        print("             wrong is the absolute PEDESTAL in (a), which is A3, not GRUNT.")
    return ped, agree, disagree


# =============================================================================================
# AD5  T3 -- 320 Hz null depth ordering
# =============================================================================================
def gate_null(rep, groups):
    print()
    print("=" * 94)
    print("AD5  TREND 3 -- the 250-800 Hz FEATURE TRAIN, model vs ND (§3)")
    print("=" * 94)
    print("  §3 states a hardware result for ONE feature in this region -- the ~320 Hz null is")
    print("  deeper on hardware in all six charted conditions.  The recovery peak and the")
    print("  bridged-T dip either side of it have NO published hardware number, so they are")
    print("  measured against ND and reported: a shape moving is worth seeing even when nothing")
    print("  adjudicates which way it should move.")
    print()
    print("  ⚠⚠ EVERY PROMINENCE BELOW IS A LOWER BOUND.  These are 3-band reads on the report's")
    print("     ~1/3-octave grid, which `measurement-discipline.md` records as having understated")
    print("     one notch by 20 dB, and the grid cannot resolve a centre to better than ~1/6 oct.")
    print("     ORDERING is graded; the VALUES are not quotable as depths or as centres.  The")
    print("     proper instruments are analysis/null_locus_gate.py (GATE R, 1/6-oct power-")
    print("     integrated depth) and analysis/feature_locus_gate.py (GATE W, log-f vertex).")
    print()

    counts = {}
    for feat, (a, b, c), kind, hw_says in FEATURE_TRAIN:
        ia, ib, ic = rep.idx(a), rep.idx(b), rep.idx(c)
        print(f"  --- {feat}  ({kind} at {b} Hz re {a}/{c} Hz) "
              + ("-- §3: HARDWARE DEEPER THAN ND" if hw_says else "-- no hardware statement"))
        print(f"      {'GRUNT':>6} {'sweep':>14} {'n':>3}  {'ND':>7} {'model':>7} {'model-ND':>9}"
              f"  verdict")
        ok = bad = 0
        ladder = {}
        for gi in (0, 1, 2):
            g = groups[f"OD bleed-free / GRUNT {GRUNT_NAME[gi]}"]
            for sw in DRIVEN:
                dm, dr = [], []
                for cap in g:
                    got = rep.raw(cap, sw)
                    if got is None:
                        continue
                    p, r = got
                    sgn = 1.0 if kind == "notch" else -1.0
                    dm.append(float(sgn * (np.nanmean([p[ia], p[ic]]) - p[ib])))
                    dr.append(float(sgn * (np.nanmean([r[ia], r[ic]]) - r[ib])))
                if not dm:
                    continue
                mm, rr = float(np.median(dm)), float(np.median(dr))
                ladder.setdefault(gi, []).append((mm, rr))
                if hw_says:
                    # §3 puts HW deeper than ND, so model SHALLOWER than ND is "expected, and
                    # still short of hardware"; model DEEPER has overshot the intermediate ref.
                    good = mm <= rr
                    verdict = "HW > ND > model (expected)" if good else "⚠ model DEEPER than ND"
                    ok, bad = (ok + 1, bad) if good else (ok, bad + 1)
                else:
                    verdict = "(reported -- nothing adjudicates)"
                print(f"      {GRUNT_NAME[gi]:>6} {sw:>14} {len(dm):3d}  {rr:7.2f} {mm:7.2f} "
                      f"{mm - rr:+9.2f}  {verdict}")

        # DRIVE DEPENDENCE of the prominence, per side.  This is the payoff of reading the whole
        # feature train rather than the 320 Hz notch alone: open work item 6 is "the pedal's
        # features move with drive and ours are pinned", and item 6 is currently stated on
        # feature CENTRES only.  Depth is a second, independent axis for the same question.
        print(f"      drive dependence of the prominence (span over the 3 driven rungs):")
        print(f"      {'GRUNT':>6}  {'ND span':>18}  {'model span':>18}")
        for gi in (0, 1, 2):
            rungs = ladder.get(gi)
            if not rungs or len(rungs) < len(DRIVEN):
                continue
            mv = [x[0] for x in rungs]
            rv = [x[1] for x in rungs]

            def fmt(v):
                mono = (all(b < a for a, b in zip(v, v[1:])) and "falling"
                        or all(b > a for a, b in zip(v, v[1:])) and "rising" or "non-mono")
                return f"{max(v) - min(v):5.2f} dB {mono:>9}"
            print(f"      {GRUNT_NAME[gi]:>6}  {fmt(rv):>18}  {fmt(mv):>18}")
        print("      ⚠ span is max-min over 3 rungs -- a RANGE, not an error bar (s129).  It")
        print("        RANKS stability; it cannot establish significance on its own.")

        if hw_says:
            counts[feat] = (ok, bad)
            print(f"      VERDICT  {ok} of {ok + bad} conditions order HW > ND > model.")
            if bad:
                print(f"               ⚠ {bad} invert.  A model deeper than ND is NOT thereby")
                print("                 closer to hardware; this estimator cannot say which, and")
                print("                 GAP #2 (the notch's depth and width) is open either way.")
        print()

    ok, bad = counts.get("320 Hz null", (0, 0))
    return ok, bad


# =============================================================================================
# AD5b  the 4.5-6 kHz null -- a feature that MOVES, so it needs a moving estimator
# =============================================================================================
def gate_hf_null(rep, groups):
    print("=" * 94)
    print("AD5b  the 4.5-6 kHz null -- POSITION and DEPTH (§1: authority = NEITHER)")
    print("=" * 94)
    print("  ⛔ `reference-sources.md` §1 lists this feature's authority as **'Neither --")
    print("     unresolved'**: it is absent from the clean sweep (so drive-dependent) and §3's")
    print("     driven charts DISAGREE between conditions -- ND ~11 dB deeper at ATTACK cut,")
    print("     hardware far deeper at GRUNT cut.  So NOTHING here is graded against hardware.")
    print("     What IS worth measuring is that the notch MOVES, and whether the two sides move")
    print("     together -- that is a shape question the capture matrix can answer today.")
    print()
    print("  ⚠ A feature that shifts cannot be read at a FIXED band (s110 GATE R: an argmin over")
    print("    a window silently changes what it tracks).  So the centre is chosen per condition")
    print("    from the window's INTERIOR bands, and an argmin resting on a window EDGE is")
    print(f"    reported as unresolved rather than as a measurement.")
    lo_hz, hi_hz = HF_NULL_WINDOW
    interior = [f for f in rep.bands if lo_hz < f < hi_hz]
    print(f"    window {lo_hz} .. {hi_hz} Hz;  interior candidates {interior}")
    print("    ⚠⚠ Those candidates are ~1/3 octave apart, so this detects a SHIFT BETWEEN BANDS")
    print("       and CANNOT locate a centre.  For a centre use feature_locus_gate.py (GATE W).")
    print()
    ilo, ihi = rep.idx(lo_hz), rep.idx(hi_hz)
    icand = [rep.idx(f) for f in interior]

    print(f"  {'GRUNT':>6} {'sweep':>14} {'n':>3}   {'ND at':>8} {'depth':>6}   "
          f"{'model at':>8} {'depth':>6}   verdict")
    moved = same = 0
    depths = {}
    for gi in (0, 1, 2):
        g = groups[f"OD bleed-free / GRUNT {GRUNT_NAME[gi]}"]
        for sw in DRIVEN:
            mc, rc = [], []
            for cap in g:
                got = rep.raw(cap, sw)
                if got is None:
                    continue
                mc.append(got[0])
                rc.append(got[1])
            if not mc:
                continue
            pm = np.nanmedian(np.array(mc), axis=0)
            pr = np.nanmedian(np.array(rc), axis=0)

            def locate(curve):
                j = min(icand, key=lambda k: curve[k])
                prom = float(np.nanmean([curve[ilo], curve[ihi]]) - curve[j])
                return float(rep.bands[j]), prom

            fr_, dr_ = locate(pr)
            fm_, dm_ = locate(pm)
            if fr_ == fm_:
                same += 1
                verdict = "same band"
            else:
                moved += 1
                verdict = f"⚠ DIFFERENT BAND ({fm_:.0f} vs {fr_:.0f} Hz)"
            depths.setdefault(gi, []).append((dm_, dr_))
            print(f"  {GRUNT_NAME[gi]:>6} {sw:>14} {len(mc):3d}   {fr_:8.0f} {dr_:6.2f}   "
                  f"{fm_:8.0f} {dm_:6.2f}   {verdict}")
    print()
    print(f"  model and ND put the null in the same band in {same} of {same + moved} conditions.")
    print("  ⇒ the SHIFT is NOT resolved at this grid.  That is a statement about the grid, not")
    print("    about the feature (s126: an 'UNRESOLVED' can be a membership property).")
    print()
    print("  DEPTH vs drive -- where the signal actually is:")
    print(f"  {'GRUNT':>6}  {'ND span':>19}  {'model span':>19}")
    frozen = 0
    for gi in (0, 1, 2):
        rungs = depths.get(gi)
        if not rungs or len(rungs) < len(DRIVEN):
            continue
        mv = [x[0] for x in rungs]
        rv = [x[1] for x in rungs]

        def fmt(v):
            mono = (all(b < a for a, b in zip(v, v[1:])) and "falling"
                    or all(b > a for a, b in zip(v, v[1:])) and "rising" or "non-mono")
            return f"{max(v) - min(v):5.2f} dB {mono:>9}"
        if max(mv) - min(mv) < 0.1:
            frozen += 1
        print(f"  {GRUNT_NAME[gi]:>6}  {fmt(rv):>19}  {fmt(mv):>19}")
    print()
    print(f"  VERDICT  the model's depth is FROZEN (span < 0.1 dB) in {frozen} of 3 GRUNT")
    print("           positions while ND's swings by up to several dB and is MONOTONE in drive.")
    if frozen:
        print("           ⚠⚠ AND READ THAT CORRECTLY: a prominence that is both TINY and")
        print("              INVARIANT TO EVERY CONTROL is the signature of NO FEATURE, not of a")
        print("              pinned one (s126 -- an extremum-finder always returns something).")
        print("              The honest statement is 'we appear to have no null here at all',")
        print("              and confirming that needs GATE W's locator, not this grid.")
    print()
    return same, moved


# =============================================================================================
# AD6  DIRECTION OF TRAVEL
# =============================================================================================
def gate_direction(t1, t2, t3, t4):
    lean_hw, lean_nd, inversions = t1
    _, agree, disagree = t2
    ok, bad = t3
    hf_same, hf_moved = t4
    print()
    print("=" * 94)
    print("AD6  DIRECTION OF TRAVEL -- the statement release_gate.py structurally cannot make")
    print("=" * 94)
    print("  T1 clean tilt      "
          + (f"TOWARD HARDWARE on {lean_hw}/{lean_hw + lean_nd} bands"
             if lean_hw > lean_nd else f"AWAY on {lean_nd}/{lean_hw + lean_nd} bands")
          + (f"; {len(inversions)} inverted" if inversions else ""))
    print("  T2 OD low-mid      "
          + ("SPAN toward hardware, PEDESTAL short (A3)" if agree and not disagree
             else f"MIXED -- {agree} agree / {disagree} disagree on sign"))
    print("  T3 320 Hz null     "
          + (f"ordered as expected in {ok}/{ok + bad}" if ok >= bad
             else f"⚠ INVERTED in {bad}/{ok + bad}"))
    print(f"  -- 4.5-6 kHz null  NOT GRADED (§1: authority = neither); model and ND agree on band "
          f"in {hf_same}/{hf_same + hf_moved}")
    print()
    print("  ⚠ This gate reports a LEAN, never a distance.  §3/§4 are PNG reads with unknown")
    print("    exact operating conditions (§6: 'we have images only, no underlying measurement")
    print("    data'), so no number here may become a fit target.")
    print()
    print("  ⛔ AND IT COVERS THREE TRENDS, NOT FOUR.  §4's harmonic finding -- hardware's")
    print("     EVEN orders sit ~27 dB above ND's while the odds match to the dB -- is the")
    print("     largest hardware gap in the project and is NOT gated here: it needs a harmonic")
    print("     instrument, not an FR one.  See analysis/matrix_harmonics.py and §4a.")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--report", default=DEFAULT_REPORT)
    args = ap.parse_args()

    if not os.path.exists(args.report):
        die("AD2", f"no such report: {args.report}")

    print()
    print("#" * 94)
    print("# GATE AD -- hardware-trend lean.  A REGRESSION GUARD, NOT A FIT TARGET.")
    print("#" * 94)

    rep = Report(args.report)
    groups = gate_membership(rep)
    ta, tb = gate_route(rep, groups)
    t1 = gate_tilt(rep, ta, tb)
    t2 = gate_lowmid(rep, groups)
    t3 = gate_null(rep, groups)
    t4 = gate_hf_null(rep, groups)
    gate_direction(t1, t2, t3, t4)
    print()


if __name__ == "__main__":
    main()
