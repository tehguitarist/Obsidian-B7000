#!/usr/bin/env python3.11
"""GATE AA -- is the model's mid peak EVIDENCE OF A MECHANISM, and what SHAPE must item 6's
candidate have?  Session 129.

It reads the STORED `s122_feature_locus.json` (GATE W) and computes.  It renders nothing and needs
no capture -- every number below was already on disk and unread, which is the point
(`check-for-unread-data-first`, seven prior occurrences).

WHY THIS EXISTS
---------------
`CLAUDE.md` open-work item 6 carries a localising clue that selects the whole shape of the item:

    "mid peak | 458 -> 429 Hz (9.0%) | 447 -> 419 Hz (8.0%) | ~2.5% -- this one TRACKS"
    "The mid peak tracking is the localising clue: we already have a drive-dependent mechanism at
     ~450 Hz and none at ~2.9 kHz, so this is not a global missing dynamic -- it is specific."

Both halves of that are read off ENDPOINTS of a per-sweep median table whose interior and whose
scatter were never printed.  This gate prints them.  Three things the summary could not say:

  * `458 -> 429` is the first and last of FOUR rungs, and the interior is 467 and 448 -- the model's
    mid peak goes UP then DOWN.  A dose-response that REVERSES is not the signature of a mechanism;
    it is what a vertex does when a neighbouring feature changes shape underneath it.  Every other
    RESOLVED model feature in the set is flat to <=0.6 %.
  * `~2.5 %` is the endpoint error.  Per rung it is +2.51 / +6.18 / +8.29 / +2.41 %.  The feature
    quoted as the one that TRACKS is 8.3 % out mid-ladder -- comparable to the treble peak's own
    19.4 % worst rung, not to the 2.5 % that got it excused.
  * GATE W5's own `spread_model_frac` for this feature is 34.1 %, against 3.0 / 2.4 / 0.8 % for the
    other three resolved features.  The 9.0 % span is drawn from a population 3.8x wider than
    itself.  (⚠ That spread is a RANGE, `max/min-1`, NOT a standard deviation -- so no sigma and no
    standard error can be computed from it, and this gate does not try.  It is quoted as what it is:
    the feature's reading is an order of magnitude less stable than any other in the set.)

WHAT SURVIVES IS CLEANER THAN WHAT DIES, AND IT IS THE RIGHT EVIDENCE FOR ITEM 6
--------------------------------------------------------------------------------
Two pedal features ARE 4/4-monotone dose-responses where the model is flat:

    bt_notch      695.7 -> 745.4 Hz   +7.15 %  RISING     model FIXED 0.15 %
    treble_peak  2696.4 -> 2498.5 Hz  -7.92 %  FALLING    model 0.21 % and itself NON-MONOTONE

⭐⭐ AND THOSE TWO ARE THE NOTCH AND THE RECOVERY PEAK OF **ONE** NETWORK (s125 localised our own
2935 Hz peak in closed form as the recovery bridged-T's rise out of its own 716 Hz notch, rolled off
by the two Sallen-Keys).  They move in OPPOSITE directions.  A linear network whose element values
scale by k moves its notch AND its recovery peak by exactly 1/k, so their RATIO is invariant -- an
effective-element-value drift can SLIDE the pair and can never COMPRESS it.  Measured, the ratio is
4/4 monotone falling, 3.876 -> 3.352, **-13.5 %**.

⇒ AA6 is a REFUTATION OF A CANDIDATE CLASS, obtained with no render and no threshold: any mechanism
that acts as a drive-dependent element VALUE -- supply sag moving a corner, a nonlinear junction
capacitance, an effective-R or effective-C drift anywhere in that network -- predicts an invariant
ratio and is refuted on SHAPE.  What compresses a bridged-T's notch-to-recovery span is a change in
its DAMPING / LOADING, not in its element values.  Same argument shape as s38's C12 locus and s125's
sign refutation: a dose-response locus that cannot contain the target refutes the lever, not just
its present setting.

⚠ THE PREMISE THIS RESTS ON, STATED SO IT IS NOT INFERRED.  "One network" is established IN CLOSED
FORM for the MODEL (s125) and ASSUMED for the pedal, on the grounds that it is the same circuit and
its two features sit at the same places (696 vs 716 Hz, 2696 vs 2977 Hz).  If the pedal's two
features are made by different networks they are free to move independently and AA6 weakens from a
refutation to an observation.  AA6 prints this caveat every run rather than burying it here.

GATES.  Hard exits cover this gate's OWN validity only; every physics outcome is a computed verdict
and execution continues (s108's rule).
--------------------------------------------------------------------------------------------
AA1  KNOWN ANSWER for the axis.  Recompute each feature/side `span_frac` from the stored medians
     and require it to reproduce GATE W6's stored value.  This is not decorative: `span_frac` is
     `max/min - 1` over the FOUR RUNGS, so a gate that mis-orders, drops or duplicates a rung
     fails here before it reports anything.  It can fail -- the mutation runner drops a rung.
AA2  MEMBERSHIP, asserted, never inferred.  The report is NAMED; the feature list must be GATE W's
     own 7; every feature must carry exactly 4 rungs per side or be named as UNRESOLVED and
     excluded EXPLICITLY.  A feature silently vanishing is what AA2 exists to catch.
AA3  STABILITY.  Each resolved feature's per-sweep span printed beside GATE W5's across-condition
     RANGE for the same side.  Computed verdict per feature: a span smaller than the range it is
     drawn from is NOT ESTABLISHED as a drive dependence.
AA4  MONOTONICITY -- the dose-response test.  4/4 rising, 4/4 falling, or NON-MONOTONE, per side.
AA5  PER-RUNG ERROR.  model-vs-pedal at every rung, so an endpoint figure can never again stand in
     for the ladder.  Verdict fires when the endpoint error understates the worst rung by >=2x.
AA6  THE ONE-NETWORK CONSTRAINT (above).  Verdict SCALING REFUTED iff the pair moves in opposite
     directions AND the ratio is monotone across all four rungs.

Run:  /opt/homebrew/bin/python3.11 analysis/drive_locus_gate.py
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))

W_REPORT = "analysis/reports/s122_feature_locus.json"
OUT_JSON = "analysis/reports/s129_drive_locus.json"

# The rung labels, in GATE W's own SWEEPS order.  ⚠ NAMED, not derived from the data -- if the
# stored report ever carries a different number of rungs AA2 must fail rather than re-label them.
RUNGS = ("clean", "drv_-18", "drv_-12", "drv_-6")

# GATE W's own feature order.  Asserted in AA2 against the report.
EXPECT_FEATURES = ("bass_notch", "bass_peak", "mid_notch", "mid_peak",
                   "bt_notch", "treble_peak", "treble_notch")

# The two features s125 localised as ONE network (its 716 Hz notch and its 2935 Hz recovery peak).
ONE_NETWORK = ("bt_notch", "treble_peak")

# AA1's tolerance.  Reproducing a stored float from the stored inputs it was computed from is exact
# arithmetic, not a measurement -- so the bar is float noise, not a physical tolerance.
KA_TOL = 1e-9

# AA5 fires when the endpoint error understates the worst rung by at least this factor.  ⚠ Not a
# guessed round number in the sense `a-threshold-you-guessed-is-not-a-guard` warns about: it is the
# point at which a quoted figure is wrong by more than itself, which is the claim AA5 makes.
ENDPOINT_UNDERSTATE_X = 2.0


def _fail(tag, msg):
    print(f"\n  ⛔ REFUSED [{tag}] {msg}")
    sys.exit(1)


def span_frac(v):
    return max(v) / min(v) - 1.0


def monotone(v):
    """4/4 rising / falling, or not a dose-response at all."""
    if len(v) < 2:
        return "n/a"
    if all(b > a for a, b in zip(v, v[1:])):
        return "RISING 4/4"
    if all(b < a for a, b in zip(v, v[1:])):
        return "FALLING 4/4"
    return "NON-MONOTONE"


def main():
    if not os.path.exists(W_REPORT):
        _fail("AA2", f"{W_REPORT} is missing -- this gate reads GATE W's stored locus, it does not "
                     f"re-render it.")
    d = json.loads(open(W_REPORT).read())
    w5, w6 = d.get("w5", {}), d.get("w6", {})
    out = {"w_report": W_REPORT, "rungs": list(RUNGS)}

    print("=" * 96)
    print("GATE AA -- the model's mid peak: mechanism, or an unstable vertex?   (session 129)")
    print("=" * 96)
    print(f"  source   {W_REPORT}   (stored GATE W; nothing is rendered here)")
    print(f"  rungs    {' -> '.join(RUNGS)}   (GATE W's SWEEPS order, NAMED not inferred)")

    # ---- AA2  MEMBERSHIP ------------------------------------------------------------------------
    got = tuple(f[0] if isinstance(f, (list, tuple)) else f for f in d.get("features", []))
    if got != EXPECT_FEATURES:
        _fail("AA2", f"feature list moved: {got} vs {EXPECT_FEATURES}")
    if set(w6) != set(EXPECT_FEATURES):
        _fail("AA2", f"w6 covers {sorted(w6)} -- expected {sorted(EXPECT_FEATURES)}")

    # ⚠ THREE outcomes, not two.  A side with ZERO rungs is genuinely UNRESOLVED (the feature has no
    # reading at all -- e.g. a mix cancellation has none bleed-free, s126's W6 lesson).  A side with
    # 1..3 rungs is a MALFORMED REPORT: data that existed and went missing.  Collapsing the second
    # into the first is how "a feature silently vanishing" -- the thing AA2 exists to catch -- gets
    # past AA2 wearing the costume of an honest exclusion.  Found by this gate's own mutation
    # runner, which aimed an arm at AA1 and was caught here instead.
    resolved, unresolved, partial = [], [], []
    for name in EXPECT_FEATURES:
        sides = {s: w6[name][s].get("medians") or [] for s in ("model", "pedal")}
        counts = {s: len(v) for s, v in sides.items()}
        if all(n == len(RUNGS) for n in counts.values()):
            resolved.append(name)
        elif all(n in (0, len(RUNGS)) for n in counts.values()):
            unresolved.append((name, counts))
        else:
            partial.append((name, counts))
    if partial:
        _fail("AA2", "PARTIAL rung coverage -- the report lost data rather than never having it: "
                     + "; ".join(f"{n} {c}" for n, c in partial)
                     + f".  Expected {len(RUNGS)} rungs or 0 per side.")
    print(f"\nAA2  MEMBERSHIP   {len(resolved)} features resolved on BOTH sides at all "
          f"{len(RUNGS)} rungs: {', '.join(resolved)}")
    for name, counts in unresolved:
        print(f"     excluded (named, not dropped): {name:<13} rungs {counts}")
    if not resolved:
        _fail("AA2", "no feature is resolved on both sides -- nothing below would mean anything.")
    out["membership"] = {"resolved": resolved,
                         "unresolved": {n: c for n, c in unresolved}}

    # ---- AA1  KNOWN ANSWER ----------------------------------------------------------------------
    # ⚠ WHAT THIS DOES AND DOES NOT TEST, because an exact 0.0 looks like a strong pass and is not
    # (s119: `a known answer an earlier sub-gate already guarantees is not a known answer`).
    # Recomputing `max/min-1` from the medians W6 computed it from is the SAME arithmetic and is
    # exact BY CONSTRUCTION -- so it is not a check on the value.  What it binds is the RUNG AXIS:
    # a dropped, duplicated or re-ordered rung changes max/min and fails here.  The second arm is
    # the one that is not guaranteed: W6's stored `verdict` string is produced by DIFFERENT code
    # from the same medians, so recomputing it at W6's own STIM_MOVE_FRAC bar cross-checks the
    # reading against a stored quantity this gate never touches.
    import feature_locus_gate as W  # noqa: E402  -- for STIM_MOVE_FRAC / GRID_STEP_FRAC, not copied
    worst, worst_where = 0.0, "(all exact)"
    vmis = []
    for name in resolved:
        for side in ("model", "pedal"):
            med = w6[name][side]["medians"]
            if len(med) != len(RUNGS):
                _fail("AA1", f"{name}/{side} has {len(med)} rungs, expected {len(RUNGS)} -- the "
                             f"axis AA1 reproduces is not the axis W6 built.")
            err = abs(span_frac(med) - w6[name][side]["span_frac"])
            if err > worst:
                worst, worst_where = err, f"{name}/{side}"
            want = "DRIVE-DEPENDENT" if span_frac(med) > W.STIM_MOVE_FRAC else "FIXED"
            if want != w6[name][side].get("verdict"):
                vmis.append(f"{name}/{side}: recomputed {want}, stored "
                            f"{w6[name][side].get('verdict')}")
    print(f"\nAA1  KNOWN ANSWER   (a) span_frac recomputed from W6's medians: worst |err| = "
          f"{worst:.3e} at {worst_where}  (bar {KA_TOL:.0e})")
    print(f"                     exact by construction -- (a) binds the RUNG AXIS (count/order), "
          f"not the value.")
    print(f"                 (b) W6's stored verdict re-derived at its own "
          f"{W.STIM_MOVE_FRAC*100:.0f} % bar: "
          f"{len(resolved)*2 - len(vmis)}/{len(resolved)*2} agree")
    if worst > KA_TOL:
        _fail("AA1", f"span_frac does not reproduce ({worst:.3e} at {worst_where}) -- this gate is "
                     f"not reading W6's rungs the way W6 wrote them.")
    if vmis:
        _fail("AA1", "recomputed verdict disagrees with W6's stored one: " + "; ".join(vmis))
    print("     PASS -- the rung axis is W6's own, on two stored quantities.")
    out["ka_worst"] = worst

    # ---- AA3 / AA4  STABILITY AND DOSE-RESPONSE -------------------------------------------------
    # ⚠⚠ THE FIRST DRAFT OF THIS BLOCK GATED THE SPAN AGAINST W5's ACROSS-CONDITION RANGE AND WAS
    # WRONG -- it compares a span of MEDIANS against a RANGE of INDIVIDUALS, so it duly reported the
    # pedal's 4/4-monotone treble walk as "NOT ESTABLISHED".  A median over 17-51 conditions is far
    # better determined than the population's full range, and a RANGE admits no error bar at all
    # (no sigma, no standard error -- `max/min-1` is not a dispersion you can divide by sqrt(n)).
    # ⇒ the range is reported as a STABILITY RANK ONLY and gates nothing.
    #
    # The floor that IS legitimate is the LOCATOR's own resolution: GATE W power-averages onto a
    # 1/48-octave grid (1.45 % per cell) and parabola-interpolates the vertex inside a cell, and
    # s126 fixed "the same reading" at a third of a cell.  A span under that is unresolvably FLAT.
    # Imported from GATE W, never transcribed.
    FLAT_FRAC = W.GRID_STEP_FRAC / 3.0
    print(f"\nAA3/AA4  per-sweep SPAN, the locator's resolution floor, and the DOSE-RESPONSE")
    print(f"     resolution floor = GRID_STEP_FRAC/3 = {FLAT_FRAC*100:.2f} %  (s126's "
          f"'same reading' bar, imported from GATE W)")
    print(f"     ⚠ `range` is GATE W5's across-condition `max/min-1` -- a RANGE, not an SD.  It "
          f"admits no error bar,\n         so it RANKS reading stability and GATES NOTHING.  The "
          f"verdict below rests on the resolution floor\n         and on monotonicity across the "
          f"four rungs.")
    print(f"\n     {'feature':<13}{'side':<7}{'span':>8}{'range':>9}  {'dose-response':<14}  verdict")
    aa34 = {}
    for name in resolved:
        for side in ("model", "pedal"):
            med = w6[name][side]["medians"]
            sp = span_frac(med)
            rng = w5.get(name, {}).get(f"spread_{side}_frac")
            mono = monotone(med)
            if sp < FLAT_FRAC:
                verdict = "FLAT (span below the locator's resolution)"
            elif mono == "NON-MONOTONE":
                verdict = "NOT A DOSE-RESPONSE (moves, but reverses)"
            else:
                verdict = f"DOSE-RESPONSE, {mono}"
            print(f"     {name:<13}{side:<7}{sp*100:7.2f}%"
                  + (f"{rng*100:8.1f}%" if rng is not None else f"{'--':>9}")
                  + f"  {mono:<14}  {verdict}")
            aa34[f"{name}/{side}"] = {"span_frac": sp, "range_frac": rng,
                                      "monotone": mono, "verdict": verdict}
        print()
    out["aa34"] = aa34
    out["flat_frac"] = FLAT_FRAC

    # The computed verdict item 6's clue actually turns on.
    mp_m = aa34.get("mid_peak/model")
    if mp_m is not None:
        others = [v["range_frac"] for k, v in aa34.items()
                  if k.endswith("/model") and not k.startswith("mid_peak")
                  and v["range_frac"] is not None]
        ratio = (mp_m["range_frac"] / max(others)) if others else float("nan")
        # The clue claims a MECHANISM at ~450 Hz in the MODEL.  A mechanism shows as a
        # dose-response; the verdict therefore turns on monotonicity, not on the range.
        clue_holds = mp_m["monotone"] != "NON-MONOTONE" and mp_m["span_frac"] >= out["flat_frac"]
        print(f"     ⇒ mid_peak/model is {mp_m['monotone']}, and its across-condition range "
              f"({mp_m['range_frac']*100:.1f} %) is {ratio:.1f}x the widest\n"
              f"       of any other resolved model feature -- the least stable reading in the set.")
        print(f"     ⇒ VERDICT on item 6's localising clue "
              f"(\"we already have a drive-dependent mechanism at ~450 Hz\"): "
              f"{'HOLDS' if clue_holds else 'NOT SUPPORTED'}")
        out["clue_holds"] = bool(clue_holds)
        out["mid_peak_range_x_next"] = ratio

    # ---- AA5  PER-RUNG ERROR --------------------------------------------------------------------
    print(f"\nAA5  PER-RUNG model-vs-pedal error   (an endpoint figure is not the ladder)")
    print(f"     {'feature':<13}" + "".join(f"{r:>10}" for r in RUNGS)
          + f"{'endpoint':>10}{'worst':>8}   verdict")
    aa5 = {}
    for name in resolved:
        mm, pp = w6[name]["model"]["medians"], w6[name]["pedal"]["medians"]
        errs = [a / b - 1.0 for a, b in zip(mm, pp)]
        endpoint = abs(errs[0])
        worst_e = max(abs(e) for e in errs)
        flag = worst_e >= ENDPOINT_UNDERSTATE_X * endpoint and endpoint > 0
        print(f"     {name:<13}" + "".join(f"{e*100:+9.2f}%" for e in errs)
              + f"{endpoint*100:9.2f}%{worst_e*100:7.2f}%   "
              + ("⚠ ENDPOINT UNDERSTATES BY "
                 f"{worst_e/endpoint:.1f}x" if flag else "endpoint is representative"))
        aa5[name] = {"per_rung": errs, "endpoint": endpoint, "worst": worst_e,
                     "endpoint_understates": bool(flag)}
    out["aa5"] = aa5

    # ---- AA6  THE ONE-NETWORK CONSTRAINT --------------------------------------------------------
    n_notch, n_peak = ONE_NETWORK
    print(f"\nAA6  THE ONE-NETWORK CONSTRAINT -- {n_notch} and {n_peak} are the notch and the "
          f"recovery peak\n     of ONE network (s125, closed form, MODEL side).")
    print(f"     ⚠ PREMISE: 'one network' is PROVEN for the model and ASSUMED for the pedal (same "
          f"circuit, features at\n         the same places).  If the pedal's two are different "
          f"networks, AA6 is an observation, not a refutation.")
    if n_notch in resolved and n_peak in resolved:
        bn = w6[n_notch]["pedal"]["medians"]
        tp = w6[n_peak]["pedal"]["medians"]
        ratios = [b / a for a, b in zip(bn, tp)]
        d_notch, d_peak = bn[-1] / bn[0] - 1.0, tp[-1] / tp[0] - 1.0
        opposite = (d_notch > 0) != (d_peak > 0)
        rmono = monotone(ratios)
        compression = ratios[-1] / ratios[0] - 1.0
        print(f"\n     {'rung':<10}{'notch Hz':>10}{'peak Hz':>10}{'peak/notch':>12}")
        for r, a, b, q in zip(RUNGS, bn, tp, ratios):
            print(f"     {r:<10}{a:10.1f}{b:10.1f}{q:12.4f}")
        print(f"\n     notch      {bn[0]:.1f} -> {bn[-1]:.1f} Hz   {d_notch*100:+.2f} %   "
              f"{monotone(bn)}")
        print(f"     peak      {tp[0]:.1f} -> {tp[-1]:.1f} Hz   {d_peak*100:+.2f} %   "
              f"{monotone(tp)}")
        print(f"     ratio      {ratios[0]:.4f}x -> {ratios[-1]:.4f}x  {compression*100:+.2f} %   "
              f"{rmono}")
        refuted = opposite and rmono != "NON-MONOTONE"
        print(f"\n     A linear network scaled by k moves BOTH features by 1/k, so the ratio is "
              f"INVARIANT under any\n     effective element-value drift.  Measured: the two move "
              f"{'OPPOSITE ways' if opposite else 'the SAME way'} "
              f"and the ratio is {rmono}.")
        say = ("REFUTED -- the pair COMPRESSES, and scaling cannot compress it" if refuted
               else "NOT REFUTED by this test")
        print(f"     ⇒ VERDICT: element-value-drift class {say}")
        if refuted:
            print(f"     ⇒ what remains: a mechanism that changes the network's DAMPING / LOADING, "
                  f"not its element values.")
        out["aa6"] = {"notch_hz": bn, "peak_hz": tp, "ratios": ratios,
                      "d_notch": d_notch, "d_peak": d_peak, "opposite": bool(opposite),
                      "ratio_monotone": rmono, "compression": compression,
                      "scaling_refuted": bool(refuted)}
    else:
        print(f"     NOT MEASURABLE -- {n_notch}/{n_peak} not both resolved on both sides.")
        out["aa6"] = {"verdict": "NOT MEASURABLE"}

    os.makedirs(os.path.dirname(OUT_JSON), exist_ok=True)
    with open(OUT_JSON, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  wrote {OUT_JSON}")
    print("=" * 96)


if __name__ == "__main__":
    main()
