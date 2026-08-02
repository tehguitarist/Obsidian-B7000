#!/usr/bin/env python3.11
"""GATE N -- are the 16 `gain-n12` OD rows still a capture defect?

Session 106.  No render: every number is a re-read of a report already on disk.

WHY THIS EXISTS
---------------
`matrix_grade` has split `OD ex gain-n12` from `OD gain-n12` since session 48, and every headline
the project quotes carries that exclusion.  The reason (docs/phase9-validation.md "Known-bad rows"):

    "The 16 `gain-n12` OD rows are a CAPTURE defect, localised session 48: their THD turnover --
     which no input or output gain can move -- differs from their normal-gain twins' by up to
     15.6 dB, and the input pad their turnover position implies is 3-9 dB, not the 12.07 the
     harness renders them at.  The fix is a re-capture of 4 files."

BOTH halves of that fix have since landed and NOBODY HAS CHECKED:

  * the harness now emits the pad -- `captures.render_args` passes `--input-trim` whenever
    `gainSessionDb` is non-zero (captures.py, "the pedal saw a quieter signal -- that must be
    reproduced with --input-trim or every [nonlinear comparison is invalid]").
  * the four exposed files were RE-CAPTURED on 2026-07-29 (session 70, "§1 4/4 gain-n12, owed
    since s48").  Session 70's own next-step (c) was "re-run the s48 THD-turnover test on the 4 new
    captures -- if they pass, the known-bad 16-row group is healed and the full OD matrix is
    judgeable for the first time since s30."  That was 35 sessions ago.

So the exclusion may have been stale for 35 sessions.  `verify-the-PREMISE-not-the-prior-session's-
framing-of-it`: re-measuring costs one command, and a stale premise selects the whole workplan.

WHAT IS MEASURED
----------------
THD turnover is a property of where the signal sits relative to the pedal's own clipping threshold.
No record gain and no output gain can move it -- which is exactly why session 48 used it, and why
it is still the right instrument.  If the `gain-n12` session really ran with the SEND 12.071 dB
down, then the pedal in an n12 file at stimulus `drv_-6` saw the same absolute level as its twin at
`drv_-18.07`, and their THD must agree.

The comparison is essentially interpolation: `drv_-6` and `drv_-18` are both measured and are
12 dB apart, so a 12.071 dB pad lands 0.071 dB off the end of the measured range.  The implied pad
is recovered by inverting the twin's own THD-vs-level curve, with a small BOUNDED extrapolation off
the end segment (EXTRAP_DB) for bands whose target sits just outside; the worst extrapolation
actually used is printed, and bands beyond the cap are dropped and counted.

  implied_pad(band) = (-6) - L*,  where  y_twin(L*) = y_n12(-6),  y = 20*log10(THD %)

  healed   => implied pad ~ 12.07   (what the harness renders)
  s48 state=> implied pad ~ 3-9     (the pedal was driven harder than the harness thinks)
  mislabel => implied pad ~ 0       (re-captured at NORMAL send; the harness now over-pads by 12 dB)

The third case matters and is why the verdict is three-way, not pass/fail: a re-capture at normal
send with the `gain-n12` filename retained would be a NEW defect wearing the old one's name.

GATES (all computed, exits non-zero on failure)
-----------------------------------------------
N1  MEMBERSHIP, asserted not assumed (the s104 L2 / s105 M2 lesson).  Exact file count, every twin
    named and required present, and the harness pad READ FROM `captures.gain_correction_db` rather
    than transcribed (`rebuild-targets-dont-transcribe`).
N2  KNOWN ANSWER, and the load-bearing one.  The harness renders the model side of an n12 file with
    `--input-trim -12.071`, so the MODEL is a deterministic 12.071 dB pad of its own twin.  Running
    the identical inversion on `plugin_pct` must therefore return 12.071.  This exercises the band
    selection, the guards and the interpolation end to end against a value that is known, non-zero
    and not the one the pedal is being tested for.  Plus a known-answer LADDER on the pedal side --
    the twin against itself is a 0 dB pad, and its drv_-12 curve declared at -6 is exactly 6 dB --
    so the inversion is calibrated at 0 / 6 / 12.071 rather than at a single value.
N3  POWER.  A pair whose twin's THD barely moves over the 12 dB span cannot discriminate 12.07 from
    3, and would report a spurious PASS.  Session 48 recorded exactly this failure for the band-
    SHAPE version of this test ("it has no discriminating power").  Power is computed per pair and
    a pair below the bar is reported as UNDERPOWERED, never as a pass.
N4  THE MEASUREMENT -- implied pad per pair, per stimulus, with band counts.
N5  ROBUSTNESS -- the verdict must survive the band floor being moved, so it is not an artefact of
    one threshold.  The sweep is ASSERTED to change the band count: a floor that excludes nothing
    prints an identical column that reads as a strong result and tests nothing.

WHAT THIS GATE CANNOT DO
------------------------
It cannot reproduce session 48's original finding: the four files were overwritten by the
re-capture, so the defective versions no longer exist on disk.  This certifies the CURRENT files
only.  It is evidence that the rows are judgeable now, NOT evidence that session 48 was wrong.

Run:
    python3.11 analysis/gain_session_gate.py analysis/reports/s99_attack_cand.json
    python3.11 analysis/gain_session_gate.py REPORT.json --json analysis/reports/s106_gain_session.json
"""
import argparse
import json
import sys

import numpy as np

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import matrix_grade as MG          # noqa: E402
import captures as CAP             # noqa: E402

DEFECT_TOKEN = "gain-n12"

# The three driven sweeps, in ascending stimulus level.  Their nominal dBFS IS the level axis.
SWEEP_LEVEL = {"sweep_drv_-18": -18.0, "sweep_drv_-12": -12.0, "sweep_drv_-6": -6.0}
SWEEPS = ["sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6"]

# A band is usable only if BOTH sides clear this.  A THD percentage at the floor is not a
# measurement, and differencing two of them manufactures a number (`ratio-statistics-need-a-
# denominator-guard`).
THD_FLOOR_PCT = 0.05

# Minimum swing, in dB of 20*log10(THD), that the twin's curve must cover across the 12 dB span for
# the inversion to resolve a pad at all.  Below this the pair is UNDERPOWERED, not passing.
MIN_POWER_DB = 3.0

# How close the recovered pad must sit to the harness's own figure to call the pair healed.  Set
# against the DISCRIMINATION, not tuned to the answer: session 48 measured 3-9 dB where the harness
# renders 12.07, so the two hypotheses are >3 dB apart and a 2 dB window separates them cleanly.
HEAL_TOL_DB = 2.0


# The sweeps sit at -18/-12/-6 and the pad is 12.071, so an n12 file's drv_-6 target lands at
# -18.071 -- 0.071 dB BELOW the measured range.  A strict in-range test therefore drops every band
# and the gate reports "no data" for a comparison that is, to any honest reading, interpolation.
# So a SMALL bounded extrapolation off the end segment is allowed, capped here and REPORTED (N4
# prints the worst actually used).  0.071 dB off a 6 dB segment is ~1 %; anything approaching this
# cap would mean the target is nowhere near the measured curve and the answer is not readable.
EXTRAP_DB = 1.5


def invert(y_twin_by_level, target_db):
    """-> (L*, extrapolation_used_dB) for the twin's log-THD curve at `target_db`, or (None, 0).

    Linear interpolation in (stimulus level dB, 20*log10 THD).  A target outside the measured range
    is solved off the nearest segment's slope and the overshoot returned, so the caller can bound
    it; beyond EXTRAP_DB the band is dropped and COUNTED.  A band is never CLAMPED to an endpoint,
    because a clamped band would silently vote for whichever bound it hit."""
    lv = sorted(y_twin_by_level)
    segs = [(a, b, y_twin_by_level[a], y_twin_by_level[b]) for a, b in zip(lv, lv[1:])]
    rising = [s for s in segs if s[3] > s[2]]
    if not rising:
        return None, 0.0                              # non-monotone everywhere: ill-posed
    for a, b, ya, yb in rising:
        if ya <= target_db <= yb:
            return a + (b - a) * (target_db - ya) / (yb - ya), 0.0
    # Outside every rising segment -- extrapolate off the nearest end, bounded.
    lo_a, lo_b, lo_ya, lo_yb = rising[0]
    hi_a, hi_b, hi_ya, hi_yb = rising[-1]
    if target_db < lo_ya:
        L = lo_a + (lo_b - lo_a) * (target_db - lo_ya) / (lo_yb - lo_ya)
        over = lo_a - L
    else:
        L = hi_a + (hi_b - hi_a) * (target_db - hi_ya) / (hi_yb - hi_ya)
        over = L - hi_b
    if over > EXTRAP_DB:
        return None, over
    return L, over


def implied_pad(caps, f_n12, f_twin, side, sweep_hi="sweep_drv_-6", target_from=None,
                ref_level=None):
    """-> (median implied pad dB, n bands used, n bands dropped, power dB) for one pair.

    `side` is 'pedal_pct' or 'plugin_pct'.  The pedal side is the measurement; the model side is
    N2's known answer, and both go through THIS function so the control cannot diverge from it.

    `target_from` overrides which FILE supplies the target curve and `ref_level` overrides the
    level that curve is DECLARED to sit at, leaving the twin's reference curve alone.  Together
    they build N2's known-answer ladder: the twin's own drv_-6 curve is a 0 dB pad of itself, and
    its drv_-12 curve declared at -6 is a synthetic EXACTLY 6 dB pad.  With the model side's
    12.071 that calibrates the inversion at three separate values instead of one.

    ⚠ The two must be decoupled.  Inverting the twin against itself returns 0 at EVERY sweep --
    correct, and useless as a 6 dB check; a first draft coupled them and failed its own ladder."""
    def thd(f, sw):
        return np.array(caps[f]["thd"][sw][side], dtype=float)

    tw = {sw: thd(f_twin, sw) for sw in SWEEPS}
    hi = thd(target_from or f_n12, sweep_hi)
    nb = len(hi)
    pads, dropped, power, extrap = [], 0, [], 0.0
    for b in range(nb):
        # `np.isfinite` FIRST and explicitly: the report carries 3 non-finite THD entries per
        # record, and `nan <= floor` is False, so a floor test alone lets them through.  They then
        # poison the power median to nan, and `nan < MIN_POWER_DB` is also False -- which silently
        # disables the UNDERPOWERED branch entirely (`empty-gate-must-fail`, found in this gate).
        vals = [hi[b]] + [tw[sw][b] for sw in SWEEPS]
        if not all(np.isfinite(v) for v in vals) or any(v <= THD_FLOOR_PCT for v in vals):
            dropped += 1
            continue
        curve = {SWEEP_LEVEL[sw]: 20.0 * np.log10(tw[sw][b]) for sw in SWEEPS}
        power.append(max(curve.values()) - min(curve.values()))
        L, over = invert(curve, 20.0 * np.log10(hi[b]))
        if L is None:
            dropped += 1
            continue
        extrap = max(extrap, over)
        pads.append((ref_level if ref_level is not None else SWEEP_LEVEL[sweep_hi]) - L)
    if not pads:
        return None, 0, dropped, (float(np.median(power)) if power else 0.0), extrap
    return float(np.median(pads)), len(pads), dropped, float(np.median(power)), extrap


def find_twin(f, caps):
    """The full-send capture of the SAME physical condition as `gain-n12` capture `f`, or None.

    ⚠⚠ SESSION 112: THIS USED TO BE A FILENAME TRANSFORM, AND NEW DATA BROKE IT — CORRECTLY.
    Session 111's DRIVE ladder at `gain-n12` includes `drive-1200_gain-n12_base-od.wav`, whose
    full-send twin is not `drive-1200_base-od.wav` (no such file) but **`ref-od.wav`**: DRIVE noon
    IS the reference baseline, so that one condition has two legitimate names. The name transform
    could only ever see one of them, and the gate hard-exited on a pair that is present.

    So resolve by SETTINGS: the twin is the capture identical in every knob and switch, differing
    only in `gainSessionDb`. That is the definition the turnover test actually needs — it compares
    two recordings of one condition at two sends — and it is immune to naming.

    The name transform is kept as the FIRST try, so every pre-s112 pairing resolves exactly as it
    did and the older quotes stay reproducible; the settings search only runs when it fails.
    ⛔ An ambiguous settings match is a hard failure, not a pick-the-first: two candidates would mean
    the matrix holds two full-send recordings of one condition, which is a membership question the
    caller must resolve (`aggregate-moved-check-membership-first`), not something to average over."""
    by_name = f.replace(f"_{DEFECT_TOKEN}", "").replace(f"{DEFECT_TOKEN}_", "")
    if by_name in caps:
        return by_name
    want = {k: v for k, v in caps[f]["settings"].items() if k != "gainSessionDb"}
    hits = [g for g, c in caps.items()
            if g != f
            and not c["settings"].get("gainSessionDb")
            and {k: v for k, v in c["settings"].items() if k != "gainSessionDb"} == want]
    if len(hits) > 1:
        sys.exit(f"GATE N1 FAIL: {f} has {len(hits)} full-send captures at identical settings "
                 f"({', '.join(sorted(hits))}) -- ambiguous twin, resolve the membership first")
    return hits[0] if hits else None


def gate_n1(caps, out):
    """Membership, asserted.  A substring filter that silently matches nothing would make every
    verdict below vacuous -- so the count is required, and every twin must exist by name."""
    print("-- N1: membership, asserted --")
    n12 = sorted(f for f in caps if DEFECT_TOKEN in f and MG.is_od(f))
    if not n12:
        sys.exit(f"GATE N1 FAIL: no OD capture matches '{DEFECT_TOKEN}' -- the filter found nothing, "
                 f"which is `empty-gate-must-fail` in a costume, not a clean bill of health")
    pairs, silent = [], []
    for f in n12:
        twin = find_twin(f, caps)
        if twin is None:
            twin_by_name = f.replace(f"_{DEFECT_TOKEN}", "").replace(f"{DEFECT_TOKEN}_", "")
            sys.exit(f"GATE N1 FAIL: {f} has no normal-gain twin (no {twin_by_name}, and no capture "
                     f"whose SETTINGS match it apart from the send) -- the turnover test is a "
                     f"twin comparison and cannot run without one")
        # A row the matrix never grades cannot be part of the 16, and must not dilute the verdict.
        # BOTH sides are tested, exactly as MG.load / level_law_gate.absolute_fr do: at LEVEL 0 it
        # is the MODEL that mutes and the PEDAL that does not (GATE L7), so a pedal-only test would
        # wrongly keep the row and then fail N2 for want of a model THD to invert.
        def _silent(fl):
            fr = caps[fl]["fr"]
            return all(max(max(fr[sw]["plugin_db"]), max(fr[sw]["pedal_db"])) < MG.SILENT_DB
                       for sw in fr) or \
                any(max(fr[sw]["plugin_db"]) < MG.SILENT_DB for sw in fr)
        if _silent(f) or _silent(twin):
            silent.append(f)
            continue
        pairs.append((f, twin))
    pad = CAP.gain_correction_db(CAP.parse_capture(n12[0]))
    print(f"    {len(n12)} `{DEFECT_TOKEN}` OD captures; {len(silent)} below SILENT_DB "
          f"(never graded, excluded): {silent}")
    print(f"    {len(pairs)} graded pairs x {len(SWEEPS)} driven sweeps = "
          f"{len(pairs) * len(SWEEPS)} rows (+{len(pairs)} clean sweep = "
          f"{len(pairs) * (len(SWEEPS) + 1)} matrix rows)")
    for f, t in pairs:
        print(f"      {f:<44} <- twin -> {t}")
    print(f"    harness pad, READ from captures.gain_correction_db: {pad:.3f} dB")
    if abs(pad) < 1.0:
        sys.exit(f"GATE N1 FAIL: harness pad {pad:.3f} dB is ~0 -- these files are not being padded "
                 f"at all, so there is no hypothesis to test")
    out["n1"] = {"n12_files": n12, "silent": silent,
                 "pairs": [list(p) for p in pairs], "harness_pad_db": pad}
    return pairs, pad


def gate_n2(caps, pairs, pad, out):
    """KNOWN ANSWER.  The model side of an n12 file IS its twin rendered with `--input-trim -pad`,
    deterministically.  So this same inversion, on `plugin_pct`, must return `pad`.  Nothing about
    the pedal enters; if this fails the instrument is broken and no pedal number below is readable."""
    print(f"\n-- N2: known answer -- the MODEL must return the harness pad ({pad:.3f} dB) --")
    print(f"    {'pair':<44}{'recovered':>11}{'err':>8}{'n':>5}")
    rec, worst, worst_ext = {}, 0.0, 0.0
    for f, t in pairs:
        p, n, _d, _pw, ext = implied_pad(caps, f, t, "plugin_pct")
        worst_ext = max(worst_ext, ext)
        if p is None:
            sys.exit(f"GATE N2 FAIL: no usable band for {f} on the model side -- an empty median is "
                     f"not a measurement")
        rec[f] = p
        worst = max(worst, abs(p - pad))
        print(f"    {f:<44}{p:>11.3f}{p - pad:>8.3f}{n:>5}")
    if worst > 1.0:
        sys.exit(f"GATE N2 FAIL: the model side recovers the harness pad only to {worst:.3f} dB. "
                 f"The inversion does not reproduce a pad it KNOWS is there, so its reading of the "
                 f"pedal cannot be trusted.  Fix the instrument before reading N4.")
    print(f"    N2 OK   worst error {worst:.3f} dB against a known {pad:.3f} dB pad "
          f"(worst extrapolation used: {worst_ext:.3f} dB of the {EXTRAP_DB} dB cap).")

    # The pad above is ONE value, and an inversion can reproduce one value by accident (a constant
    # would).  Calibrate it at two further KNOWN pads, on the PEDAL side, using the twin against
    # itself: its own drv_-6 curve is 0 dB away and its own drv_-12 curve is exactly 6 dB away.
    # Three known answers at 0 / 6 / 12.071 is a ladder; one is an anecdote.
    print(f"\n    known-answer ladder (pedal side, twin inverted against itself):")
    print(f"    {'pair':<44}{'@-6 (=0)':>11}{'@-12 (=6)':>12}")
    lad = {}
    for f, t in pairs:
        p0, *_ = implied_pad(caps, f, t, "pedal_pct", target_from=t)
        # The twin's own drv_-12 curve, DECLARED to sit at -6: a synthetic, exactly-6 dB pad.
        p6, *_ = implied_pad(caps, f, t, "pedal_pct", sweep_hi="sweep_drv_-12", target_from=t,
                             ref_level=-6.0)
        if p0 is None or p6 is None:
            sys.exit(f"GATE N2 FAIL: known-answer ladder returned no data for {t}")
        lad[f] = (p0, p6)
        print(f"    {f:<44}{p0:>11.4f}{p6:>12.4f}")
        if abs(p0) > 0.01 or abs(p6 - 6.0) > 0.01:
            sys.exit(f"GATE N2 FAIL: the inversion does not reproduce a pad it constructed itself "
                     f"({p0:.4f} should be 0, {p6:.4f} should be 6).  Its 12.071 recovery above is "
                     f"therefore not evidence of anything.")
    print(f"    N2 ladder OK   0 and 6 dB pads recovered exactly; with the 12.071 above, the")
    print(f"                   inversion is calibrated across the whole range it is used over.")
    out["n2"] = {"recovered": rec, "worst_err_db": worst,
                 "ladder": {k: list(v) for k, v in lad.items()}}


def gate_n3_n4_n5(caps, pairs, pad, out):
    """Power, then the measurement, then the floor-robustness column."""
    print("\n-- N3/N4: power, then the implied pad on the PEDAL --")
    print(f"    {'pair':<44}{'power':>8}{'implied':>9}{'vs harness':>12}{'n':>5}{'drop':>6}  verdict")
    rows, verdicts = {}, []
    for f, t in pairs:
        p, n, d, pw, ext = implied_pad(caps, f, t, "pedal_pct")
        if not np.isfinite(pw):
            sys.exit(f"GATE N3 FAIL: power is non-finite for {f}.  A non-finite power silently "
                     f"disables the UNDERPOWERED branch (every comparison against it is False), so "
                     f"the gate would report a PASS it never tested.  Fix the band guard.")
        if p is None:
            v = "NO DATA"
        elif pw < MIN_POWER_DB:
            v = "UNDERPOWERED"
        elif abs(p - pad) <= HEAL_TOL_DB:
            v = "HEALED"
        elif p < pad - HEAL_TOL_DB:
            v = "STILL DEFECTIVE"
        else:
            v = "OVER-PADDED"
        verdicts.append(v)
        rows[f] = {"implied_pad_db": p, "power_db": pw, "n_bands": n, "dropped": d,
                   "extrap_db": ext, "verdict": v}
        ps = f"{p:>9.3f}" if p is not None else f"{'--':>9}"
        print(f"    {f:<44}{pw:>8.2f}{ps}{(p - pad) if p is not None else float('nan'):>12.3f}"
              f"{n:>5}{d:>6}  {v}")

    print("\n-- N5: robustness -- the verdict must survive the THD floor moving --")
    # ⚠ The floor must be swept over a range that BINDS.  A first draft swept 0.02-0.20 % and
    # printed four identical columns, which reads as a strong robustness result and was nothing of
    # the kind: the lowest real THD here is ~0.25 %, so no band was ever excluded and the knob was
    # not turning (`an implausible coincidence is a bug report`, s105 M4).  The band count is now
    # printed and the sweep is asserted to actually change it.
    global THD_FLOOR_PCT
    keep = THD_FLOOR_PCT
    print(f"    {'floor %':>9}" + "".join(f"{f.split('_')[0][:12]:>16}" for f, _ in pairs))
    rob, counts = {}, []
    for fl in (0.05, 0.50, 1.00, 2.00):
        THD_FLOOR_PCT = fl
        vals, ns = [], 0
        for f, t in pairs:
            p, n, *_ = implied_pad(caps, f, t, "pedal_pct")
            vals.append(p)
            ns += n
        counts.append(ns)
        rob[fl] = [None if v is None else round(v, 3) for v in vals]
        print(f"    {fl:>9.2f}" + "".join(f"{v:>11.3f}" if v is not None else f"{'--':>11}"
                                          for v in vals) + f"   [{ns} bands]")
    THD_FLOOR_PCT = keep
    if len(set(counts)) == 1:
        sys.exit(f"GATE N5 FAIL: the floor sweep never changed the band count ({counts[0]} at every "
                 f"floor) -- the knob is not turning, so this column is not a robustness check.")
    spread = [max(v for v in rob[fl] if v is not None) - min(v for v in rob[fl] if v is not None)
              for fl in rob]
    print(f"    N5 OK   band count moves {counts[0]} -> {counts[-1]}, so the floor binds; the "
          f"per-floor pair spread stays {min(spread):.2f}-{max(spread):.2f} dB.")

    out["n3_n4"] = rows
    out["n5_floor_robustness"] = {str(k): v for k, v in rob.items()}

    # ---- computed verdict.  Narrating this would be `computed-verdicts-not-narrated`. ----
    scored = [v for v in verdicts if v not in ("NO DATA", "UNDERPOWERED")]
    healed = [v for v in scored if v == "HEALED"]
    print("\n== VERDICT ==")
    print(f"    {len(healed)} of {len(scored)} discriminating pairs read HEALED "
          f"({len(verdicts) - len(scored)} not scored: underpowered or no data)")
    if not scored:
        sys.exit("GATE N FAIL: no pair had the power to discriminate -- this is NOT a pass, it is "
                 "an instrument with no resolution (session 48 recorded exactly this failure for "
                 "the band-SHAPE version of the test).")
    if len(healed) == len(scored):
        print(f"    => every discriminating pair recovers the harness's own {pad:.3f} dB pad to "
              f"within {HEAL_TOL_DB} dB.  Session 48's finding -- an implied pad of 3-9 dB -- does")
        print( "       NOT reproduce on these files.  The re-capture worked and the 16-row")
        print( "       exclusion is STALE.")
        print( "    ⚠ This certifies the CURRENT files only.  The defective versions were")
        print( "       overwritten by the 2026-07-29 re-capture, so session 48's original")
        print( "       measurement cannot be reproduced and is NOT contradicted by this.")
    else:
        bad = [f for f, r in rows.items() if r["verdict"] not in ("HEALED", "UNDERPOWERED", "NO DATA")]
        print(f"    => NOT healed.  Still-defective pairs: {bad}")
    out["verdict"] = {"healed": len(healed), "scored": len(scored), "all_healed": len(healed) == len(scored)}


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("report")
    ap.add_argument("--json")
    args = ap.parse_args()

    _bands, caps = MG.load(args.report)
    out = {"report": args.report, "n_captures": len(caps)}
    print(f"GATE N -- are the `{DEFECT_TOKEN}` OD rows still a capture defect?   [{args.report}]")
    print(f"  {len(caps)} captures\n")

    pairs, pad = gate_n1(caps, out)
    gate_n2(caps, pairs, pad, out)
    gate_n3_n4_n5(caps, pairs, pad, out)

    print("\n== GATE N: all sub-gates passed ==")
    if args.json:
        json.dump(out, open(args.json, "w"), indent=1)
        print(f"   wrote {args.json}")


if __name__ == "__main__":
    main()
