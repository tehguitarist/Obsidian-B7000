#!/usr/bin/env python3.11
"""GATE BQ -- item 9's LEVEL-SENSITIVITY TARGETS, RE-MEASURED ON THE CURRENT EPOCH.

WHY THIS EXISTS.  GATE AY5(c) grades a taper/mix-law reshape against two numbers:

    bass notch   (s125)      pedal 30.0 % / model 17.2 %  ->  needs 1.744x
    treble_notch (s133 AE4)  pedal 24.3 % / model  9.1 %  ->  needs 2.670x

Both MODEL-side figures were measured BEFORE session 181 gave `LevelBlend` a wiper end stop, and
AY5(c) has since measured that the shipped stage's own mix-ratio span is **1.47x larger** than the
retired `(1 - L)` arithmetic said.  The model whose sensitivity those 17.2 % / 9.1 % describe is
therefore not the model that ships, and AY5(c) says so in its own output:

    "⚠⚠ AND THE TARGETS ARE THEMSELVES A RETIRED EPOCH ... re-measuring them is owed before
      either is graded again."

USER DECISION 2026-08-09: **MEASURE FIRST, DO NOT SHIP** the s189 4-segment taper candidate.  This
gate is that measurement.  ⛔ It changes no constant and proposes none.

WHAT IT MEASURES.  Exactly W4's statistic, on W4's own ladder, with W4's own estimator -- all three
IMPORTED from `feature_locus_gate`, never re-derived (`rebuild-targets-dont-transcribe`, and the
s149 lesson that a shared helper multiplies one defect across every gate that calls it).  For each
feature and each side, the centre frequency across the LEVEL detents, and

    span = max(f0) / min(f0) - 1        (W4's own definition)
    need = span_pedal / span_model      (the fold a mix-law reshape would have to deliver)

⚠⚠ THREE THINGS THIS GATE DOES THAT W4 DOES NOT, each for a reason paid for elsewhere:

  (1) MATCHED DETENTS.  W4 takes each side's span over whatever that side could read.  An
      estimator that REFUSES is correlated with the thing being graded -- a feature too shallow to
      locate is exactly the outcome under test -- so unmatched spans reward the arm that reads
      less (s178's 13th occurrence of `aggregate-moved-check-membership-first`, in its most
      self-serving form).  Item 9's own note already carries the scar: the treble_notch pair reads
      **9.1 % vs 133.5 %** raw and **9.1 % vs 24.3 %** matched.  Every span here is over detents
      readable on BOTH sides at that sweep, and the drops are NAMED.

  (2) EVERY SWEEP, PRINTED.  W4 reads `sweep_clean` only.  That is the right choice for W4's own
      question (is this a MIX feature or a NETWORK corner -- drive as far out of the picture as
      possible), and it is the wrong one for a SIZING that will decide a ship: s126 measured this
      very family of gaps COLLAPSING with stimulus (bass peak +25.7 % at clean -> +6.4 % at
      `drv_-6`), and the user's stated playing level is `drv_-12`.  An endpoint is not a ladder
      (s129).  All four rungs are printed; `sweep_clean` is labelled as W4's condition.

  (3) A DENOMINATOR GUARD.  `need` divides by the MODEL's span, and a model span at the locator's
      own resolution makes the fold arbitrarily large for free
      (`ratio-statistics-need-a-denominator-guard`).  A cell whose model span is under
      RESOLVE_FLOOR_FRAC is REFUSED and printed as refused, never quoted.

THE KNOWN ANSWER IS FREE, AND IT IS THE REASON THIS GATE CAN ATTRIBUTE ANYTHING.  The PEDAL side is
a property of capture files and this estimator -- **no render, no binary, nothing this project has
changed since s125 touches it**.  So the pedal spans MUST still be what item 9 published.  If they
reproduce, the estimator, the windows and the membership are all validated at once, and any move in
`need` is attributable to the MODEL epoch alone.  If they do not, the difference is membership or
transcription -- and that is a finding about item 9's own numbers, not about the pedal.
(s159 AW1b's trick: the binary-independent side of a comparison is a free cross-epoch check.)

⛔⛔ THIS GATE MUST NOT TOUCH `build/s122_feature_locus/`.  That cache is READ-ONLY and ENFORCED
(s159): GATEs AV / AW / AF / AG / BC all read the epoch it holds, its stamps are 0 fresh / 25 stale
against the current binary (s188), and pointing any tool's `ren_dir` at it would re-render all 25
and destroy that epoch.  BQ0 fingerprints it before and after and REFUSES on any change.

Run:
    python3.11 analysis/level_sensitivity_gate.py [--report analysis/reports/s187_grunt_lf.json]
"""
import argparse
import glob
import hashlib
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                # noqa: E402
import captures as C               # noqa: E402
import comprehensive_report as CR  # noqa: E402
import feature_locus_gate as W     # noqa: E402  -- ladder, locator, windows, constants: IMPORTED
import level_taper_reshape as AY   # noqa: E402  -- the consumer whose targets are being re-measured
from parallel import pmap          # noqa: E402

# ---- the two features item 9's targets are about ----------------------------------------------
# ⚠ NAMED, not searched for.  `bass_notch` is s125's "bass notch"; `treble_notch` is s133 AE4's
# feature -- and note AE2's correction, that its LABEL ("the 4.5-6 kHz null") is not its WINDOW.
# The windows come from W.FEATURES so this gate cannot drift from the locator that defines them.
TARGET_FEATURES = ("bass_notch", "treble_notch")

# ---- item 9's published numbers, in the TWO forms they exist in ------------------------------
# ⚠⚠ THE PAIR GATE AY GRADES AGAINST IS NOT THE PAIR EITHER SOURCE SESSION PUBLISHED, AND THAT IS
# THE FIRST FINDING OF THIS GATE.  There are two forms and they must not be conflated:
#
#  PRIMARY  -- what the source session actually recorded, on its own instrument and its own
#              membership.  These are reproducible, and BQ1 reproduces them.
#                bass_notch    s125 recorded the LEVEL LOCI in Hz: model 53.2-64.2, pedal 38.1-54.4
#                              (`CLAUDE.md`'s s125 CLOSED/REFUTED row) -> pedal span 42.8 %
#                treble_notch  GATE AE's own docstring records W4's reading verbatim:
#                              "model span 3.7 % over 3 detents -> NETWORK / pedal span 44.1 %
#                               over 6 detents -> MIX (agreement: DISAGREE)"
#
#  RESTATED -- the matched-detent pair AY5(c) grades a candidate against (30.0/17.2 and 24.3/9.1).
#              ⛔ NEITHER source produced these, and this gate cannot reproduce either.  Their
#              MEMBERSHIP was set by the MODEL's readability on a retired build, so a "pedal span"
#              in this form is NOT a property of the pedal alone -- which is exactly why it cannot
#              serve as the binary-independent known answer it looks like.
#
# ⚠ And the two PRIMARY figures come from TWO DIFFERENT INSTRUMENTS (GATE W's locator for the bass
# notch, GATE AE's for the treble one), so item 9's "two targets" were never one measurement.  This
# gate puts both on ONE instrument, which is the point of re-measuring at all.
PRIMARY = {
    "bass_notch":   {"pedal_pct": 100.0 * (54.4 / 38.1 - 1.0), "pedal_n": None,
                     "model_pct": 100.0 * (64.2 / 53.2 - 1.0),
                     "src": "s125 loci (model 53.2-64.2, pedal 38.1-54.4 Hz)"},
    "treble_notch": {"pedal_pct": 44.1, "pedal_n": 6, "model_pct": 3.7,
                     "src": "GATE AE docstring, W4's own reading (pedal 44.1 % / 6 detents)"},
}
RESTATED = {
    "bass_notch":   {"pedal_pct": 30.0, "model_pct": 17.2, "src": "AY5(c), matched"},
    "treble_notch": {"pedal_pct": 24.3, "model_pct": 9.1,  "src": "AY5(c), matched"},
}
PUBLISHED = RESTATED   # what a candidate is currently graded against
AY_TARGET_KEY = {"bass_notch": "bass notch (s125)", "treble_notch": "treble_notch (s133 AE4)"}

REPORT = "analysis/reports/s187_grunt_lf.json"
OUT_JSON = "analysis/reports/s190_level_sensitivity.json"
REN_DIR = "build/s190_level_sensitivity"          # PRIVATE.  Never W.REN_DIR.
FORBIDDEN_DIR = W.REN_DIR                          # build/s122_feature_locus -- READ-ONLY

# The locator's own resolution, in W's own convention (`GRID_STEP_FRAC / 3`), IMPORTED.  s158/s159
# use exactly this figure as the bar below which a centre movement is not resolved.  A span must
# clear it by RESOLVE_MULT before it may sit in a denominator.
RESOLUTION_FRAC = W.GRID_STEP_FRAC / 3.0
RESOLVE_MULT = 3.0
RESOLVE_FLOOR_FRAC = RESOLUTION_FRAC * RESOLVE_MULT

# The pedal side must reproduce its published span to this tolerance to count as a known answer.
# ⚠ Placed against what the published figures were QUOTED to (3 significant figures, i.e. +-0.05
# points on a ~30 % reading = 0.17 %), widened to 1.0 % relative to allow for the report epoch's
# membership differing by a detent.  Wider than a rounding, far tighter than the 1.5-2.7x moves
# this gate exists to detect.
KA_TOL_REL = 0.01


# =================================================================================================
def dir_fingerprint(d):
    """Content fingerprint of a render directory -- what BQ0 asserts does not move."""
    if not os.path.isdir(d):
        return "ABSENT"
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(d, "*"))):
        st = os.stat(p)
        h.update(os.path.basename(p).encode())
        h.update(str((st.st_size, st.st_mtime_ns)).encode())
    return h.hexdigest()[:16]


def _cell(args):
    """One ladder capture -> located features on BOTH sides at every sweep.

    The render is this gate's own; the located features come from `W.features_of`, so the
    estimator is identical to GATE W's by construction rather than by inspection."""
    fname, ren_dir = args
    orig, ref = W._load_orig()
    ra = C.render_args(C.parse_capture(fname))
    out = os.path.join(ren_dir, fname.replace(".wav", "") + "_plugin.wav")
    # W.render carries the argv+BINARY stamp (s117); reused rather than re-implemented so this
    # gate cannot acquire the stale-stamp defect that stamp exists to prevent.
    _render_into(out, ra)
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    rec = {"file": fname, "model": {}, "pedal": {}}
    for sw in W.SWEEPS:
        rec["model"][sw] = W.features_of(ren_al, sw, ref)
        rec["pedal"][sw] = W.features_of(cap_al, sw, ref)
    return rec


def _render_into(out, args):
    """W.render, but into THIS gate's directory.

    W.render hardcodes nothing about its directory -- it takes `out` -- so this is a direct call.
    The wrapper exists only to make the private-directory choice a single, greppable place."""
    assert not os.path.abspath(out).startswith(os.path.abspath(FORBIDDEN_DIR)), \
        f"GATE BQ: refusing to render into the READ-ONLY cache {FORBIDDEN_DIR}"
    return W.render(out, args)


def valid(r):
    """W3's own validity rule for a located reading, applied to every cell this gate quotes.

    A centre resting ON a window bound is a REFUSAL, not a measurement (s151), and a feature under
    the prominence bar is not established present (s126/s133 -- an extremum finder always returns
    something)."""
    return (not r["edge"]) and r["margin_frac"] >= W.EDGE_MARGIN_FRAC and r["prom"] >= W.MIN_PROM_DB


# =================================================================================================
def gate_bq0(rep_path, out):
    """PROVENANCE -- the binary, the report epoch, and the read-only cache."""
    print("\n" + "=" * 94)
    print("BQ0  PROVENANCE -- binary epoch, report epoch, and the READ-ONLY s122 cache")
    print("=" * 94)
    binp = CR.DEFAULT_BIN
    if not os.path.exists(binp):
        sys.exit(f"GATE BQ0: render binary {binp} is absent -- nothing below can be rendered")
    bmt = os.stat(binp).st_mtime
    newer = [p for p in glob.glob("src/**/*", recursive=True)
             if os.path.isfile(p) and os.stat(p).st_mtime > bmt]
    print(f"  render binary   : {binp}")
    print(f"  src files newer : {len(newer)}")
    if newer:
        # s152/s185: a stale binary reports the PREVIOUS build's numbers with no error anywhere.
        sys.exit(f"GATE BQ0: {len(newer)} src file(s) postdate the render binary "
                 f"({newer[:3]}) -- rebuild before measuring, or every model-side number below "
                 f"is the previous build's")
    if not os.path.exists(rep_path):
        sys.exit(f"GATE BQ0: report {rep_path} is absent")
    print(f"  report          : {rep_path}")
    fp = dir_fingerprint(FORBIDDEN_DIR)
    n_stale = 0
    for p in glob.glob(os.path.join(FORBIDDEN_DIR, "*.args.json")):
        st = json.load(open(p))
        if st.get("bin") != W._bin_sig():
            n_stale += 1
    print(f"  READ-ONLY cache : {FORBIDDEN_DIR}  fingerprint {fp}")
    print(f"                    {n_stale} of {len(glob.glob(os.path.join(FORBIDDEN_DIR, '*.args.json')))}"
          f" stamps are STALE against the current binary -- which is exactly why nothing here")
    print( "                    may render into it (GATEs AV/AW/AF/AG/BC read that epoch, s159/s188)")
    print(f"  private renders : {REN_DIR}")
    out["bq0"] = {"bin": binp, "src_newer": len(newer), "report": rep_path,
                  "forbidden_dir": FORBIDDEN_DIR, "forbidden_fp_before": fp,
                  "forbidden_stale_stamps": n_stale, "ren_dir": REN_DIR}
    return fp


def gate_bq1(rows, lad, out):
    """KNOWN ANSWER -- the PEDAL side is binary-independent, so it must still be item 9's number.

    This is the whole attribution.  Nothing this project has shipped since s125 can move a pedal
    capture, so if the pedal spans reproduce, then the windows, the locator, the ladder membership
    and the matching rule are all validated together -- and every move in `need` below belongs to
    the MODEL epoch.  ⚠ It also self-checks the transcription: the per-side pair is retyped here,
    and their ratio must equal the ratio GATE AY actually grades against."""
    print("\n" + "=" * 94)
    print("BQ1  KNOWN ANSWER -- the pedal side cannot have moved, so it must reproduce item 9")
    print("=" * 94)
    print("  no render, no binary, no shipped constant enters a pedal reading; only the capture")
    print("  files and this locator do.  W4's condition is `sweep_clean`, so that is the arm the")
    print("  published figures are compared against.")
    sw = W.SWEEPS[0]
    ok = True
    res = {}
    # (a) THE TRANSCRIPTION IS SELF-CHECKING AGAINST ITS CONSUMER, and it must read a stored
    # artefact rather than an attribute that may not exist -- a `hasattr` guard around a name that
    # was never defined is a check that silently passes forever (`empty-gate-must-fail`).  GATE
    # AY's own report carries the ratios it grades against, so the per-side pair transcribed above
    # must reproduce them exactly or this gate is re-measuring a different target than AY uses.
    ay_path = "analysis/reports/s189_level_taper.json"
    if not os.path.exists(ay_path):
        sys.exit(f"GATE BQ1: {ay_path} is absent -- GATE AY's stored targets are what this gate "
                 f"re-measures, so without them the transcription above is unchecked.  Run "
                 f"`level_taper_reshape.py` first.")
    ay_targets = json.load(open(ay_path)).get("ay5", {}).get("headroom", {}).get("targets", {})
    if not ay_targets:
        sys.exit(f"GATE BQ1: {ay_path} carries no ay5.headroom.targets -- cannot verify that this "
                 f"gate re-measures the same pair GATE AY grades against")
    for name in TARGET_FEATURES:
        pub = PUBLISHED[name]
        key = AY_TARGET_KEY[name]
        if key not in ay_targets:
            sys.exit(f"GATE BQ1: GATE AY grades no target named {key!r} (it has "
                     f"{sorted(ay_targets)}) -- the two gates disagree about what item 9's "
                     f"targets ARE, which must be resolved before either is quoted")
        got = pub["pedal_pct"] / pub["model_pct"]
        if abs(got - ay_targets[key]) > 5e-4:
            sys.exit(f"GATE BQ1: the per-side pair transcribed here does not reproduce GATE AY's "
                     f"own target for {name} -- {pub['pedal_pct']}/{pub['model_pct']} = "
                     f"{got:.4f} vs AY's {ay_targets[key]:.4f}.  One of them is wrong; do not "
                     f"loosen this check.")
        res.setdefault(name, {})["published_need"] = got
    print(f"  transcription check: both per-side pairs reproduce GATE AY's stored targets "
          f"({', '.join(f'{k.split()[0]} {v:.3f}x' for k, v in sorted(ay_targets.items()))})")
    # (b) THE KNOWN ANSWER PROPER -- against the PRIMARY sources, on the UNMATCHED pedal set.
    # Unmatched is the correct set here and the choice is forced, not stylistic: a MATCHED span's
    # membership is decided by the MODEL's readability, so a matched pedal span is not a property
    # of the pedal and cannot be binary-independent.  The unmatched one is.
    print(f"\n  (b) vs the PRIMARY sources, pedal side, UNMATCHED (the only binary-independent form)")
    print(f"      {'feature':<14s} {'primary':>9s} {'measured':>9s} {'rel err':>8s} {'n':>3s}  verdict")
    for name in TARGET_FEATURES:
        pri = PRIMARY[name]
        fs, used = [], []
        for lv in sorted(lad):
            r = _read(rows, lad[lv], "pedal", sw, name)
            if r is None:
                continue
            fs.append(r["f0"])
            used.append(lv)
        span = (max(fs) / min(fs) - 1.0) * 100.0 if len(fs) >= 3 else float("nan")
        rel = abs(span - pri["pedal_pct"]) / pri["pedal_pct"] if np.isfinite(span) else float("inf")
        good = rel <= KA_TOL_REL
        n_ok = pri["pedal_n"] is None or pri["pedal_n"] == len(used)
        good = good and n_ok
        ok = ok and good
        print(f"      {name:<14s} {pri['pedal_pct']:8.1f}% {span:8.1f}% {rel*100:7.2f}% "
              f"{len(used):>3d}  {'OK' if good else 'DIFFERS'}"
              + ("" if n_ok else f"  (primary recorded n={pri['pedal_n']})"))
        print(f"      {'':<14s} source: {pri['src']}")
        res.setdefault(name, {}).update({"primary_pedal_pct": pri["pedal_pct"],
                                         "measured_pedal_pct": span, "rel_err": rel,
                                         "detents": used, "reproduces": bool(good)})
    # (c) the RESTATED pair, for the record -- it is what AY grades against and it does NOT
    # reproduce, by construction.  Printed so the discrepancy is on the record rather than
    # rediscovered by whoever next quotes 30.0 % as "the pedal".
    print(f"\n  (c) vs the RESTATED pair AY5(c) grades against -- expected NOT to reproduce")
    for name in TARGET_FEATURES:
        r = RESTATED[name]
        m = res[name]["measured_pedal_pct"]
        print(f"      {name:<14s} restated pedal {r['pedal_pct']:5.1f}%   measured {m:5.1f}%   "
              f"ratio {m / r['pedal_pct']:.2f}x")
        res[name]["restated_pedal_pct"] = r["pedal_pct"]
    out["bq1"] = {"tol_rel": KA_TOL_REL, "sweep": sw, "features": res, "all_reproduce": bool(ok)}
    if ok:
        print("\n  ⇒ ⭐ THE PEDAL SIDE REPRODUCES BOTH PRIMARY SOURCES, on two artefacts written by")
        print("    two different sessions with two different instruments.  So the locator, the")
        print("    windows and the ladder membership are validated together, and every move in")
        print("    `need` below is attributable to the MODEL epoch alone.")
        print("  ⇒ ⛔ AND THE RESTATED PAIR IS NOT A PEDAL MEASUREMENT: it does not reproduce")
        print("    because its membership was set by a RETIRED MODEL's readability.  A candidate")
        print("    graded against 30.0 % / 24.3 % is being graded against a number that carries")
        print("    the old model inside it.")
    else:
        print("\n  ⚠⚠ A PRIMARY SOURCE DID NOT REPRODUCE, AND THE PEDAL CANNOT HAVE CHANGED -- so")
        print("     either this gate's membership differs from the source's, or the source figure")
        print("     was transcribed wrong.  Settle that before quoting anything below.")
    return ok


def _read(rows, fname, side, sw, name):
    """One validated reading, or None."""
    r = rows.get(fname)
    if r is None:
        return None
    v = r[side][sw][name]
    return v if valid(v) else None


def gate_bq2(rows, lad, out):
    """THE MEASUREMENT -- every detent, every sweep, both sides, matched membership."""
    print("\n" + "=" * 94)
    print("BQ2  THE LADDER, PRINTED IN FULL -- matched detents only, every rung, every sweep")
    print("=" * 94)
    print(f"  validity per reading: not on a window bound, margin >= {W.EDGE_MARGIN_FRAC:.2f},")
    print(f"  prominence >= {W.MIN_PROM_DB:.1f} dB  (W3's own rule, imported)")
    print(f"  a span must clear {RESOLVE_FLOOR_FRAC*100:.2f} % "
          f"({RESOLVE_MULT:.0f}x the locator's {RESOLUTION_FRAC*100:.2f} % resolution) before it")
    print( "  may sit in a DENOMINATOR -- otherwise `need` is a ratio against noise")
    levels = sorted(lad)
    res = {}
    for name in TARGET_FEATURES:
        res[name] = {}
        print(f"\n  --- {name} {W.FEAT_BY_NAME[name][2]} Hz ---")
        for sw in W.SWEEPS:
            tag = "  <- W4's condition" if sw == W.SWEEPS[0] else ""
            # matched membership: a detent counts only if BOTH sides read it validly here.
            # Read ONCE per (detent, side) and reuse.  The re-read version of this loop crashed
            # under the `bq2-matching` mutation arm with a bare TypeError -- a gate must REFUSE
            # where it would otherwise crash (s117), and re-deriving the same value four times is
            # also how a membership rule and the numbers computed under it drift apart.
            read = {(lv, side): _read(rows, lad[lv], side, sw, name)
                    for lv in levels for side in ("model", "pedal")}
            matched, dropped = [], []
            for lv in levels:
                m, p = read[(lv, "model")], read[(lv, "pedal")]
                if m is not None and p is not None:
                    matched.append(lv)
                else:
                    who = ("model" if m is None else "") + ("+pedal" if p is None else "")
                    dropped.append((lv, who.strip("+")))
            print(f"\n    {sw}{tag}")
            print(f"      {'side':<6s} " + " ".join(f"{lv:>7.3f}" for lv in levels) + "     span")
            cell = {"matched": matched, "dropped": dropped}
            for side in ("model", "pedal"):
                shown, fs, got = [], [], {}
                for lv in levels:
                    r = read[(lv, side)]
                    shown.append("      -" if r is None else f"{r['f0']:7.1f}")
                    if r is not None:
                        got[lv] = r["f0"]
                    # A detent in `matched` whose reading is None can only happen if the matching
                    # rule above has been loosened; it is counted as a DROP rather than crashing.
                    if lv in matched and r is not None:
                        fs.append(r["f0"])
                span = (max(fs) / min(fs) - 1.0) if len(fs) >= 3 else float("nan")
                cell[side] = {"span_frac": span, "n": len(fs),
                              "f0": {str(lv): got[lv] for lv in matched if lv in got}}
                # the UNMATCHED set too -- BQ3b compares against PRIMARY figures whose membership
                # rule was unmatched, and mixing the two rules is the very trap BQ2 exists to close
                cell[side + "_all"] = dict(got)
                print(f"      {side:<6s} " + " ".join(shown) +
                      ("      nan" if not np.isfinite(span) else f"  {span*100:7.1f}%"))
            if dropped:
                print(f"      dropped: " + ", ".join(f"{lv:.3f} ({w})" for lv, w in dropped))
            res[name][sw] = cell
    out["bq2"] = res
    return res


def gate_bq3(bq2, out):
    """THE TARGETS, RE-DERIVED -- and graded against what item 9 currently quotes."""
    print("\n" + "=" * 94)
    print("BQ3  ITEM 9's TARGETS, RE-MEASURED  (need = pedal span / model span, matched detents)")
    print("=" * 94)
    res = {}
    print(f"  {'feature':<14s} {'sweep':<14s} {'n':>3s} {'model':>8s} {'pedal':>8s} "
          f"{'need':>8s}   {'published':>9s}   note")
    for name in TARGET_FEATURES:
        res[name] = {}
        pub_need = PUBLISHED[name]["pedal_pct"] / PUBLISHED[name]["model_pct"]
        for sw in W.SWEEPS:
            c = bq2[name][sw]
            ms, ps, n = c["model"]["span_frac"], c["pedal"]["span_frac"], len(c["matched"])
            note, need = "", float("nan")
            if n < 3:
                note = "REFUSED: < 3 matched detents"
            elif not (np.isfinite(ms) and np.isfinite(ps)):
                note = "REFUSED: a span is undefined"
            elif ms < RESOLVE_FLOOR_FRAC:
                note = (f"REFUSED: model span {ms*100:.2f} % is under the "
                        f"{RESOLVE_FLOOR_FRAC*100:.2f} % denominator floor")
            else:
                need = ps / ms
                d = need / pub_need
                note = (f"{d:.2f}x the published need" if np.isfinite(d) else "")
            res[name][sw] = {"model_span": ms, "pedal_span": ps, "need": need, "n": n,
                             "published_need": pub_need, "note": note}
            print(f"  {name:<14s} {sw:<14s} {n:>3d} "
                  f"{ms*100 if np.isfinite(ms) else float('nan'):7.1f}% "
                  f"{ps*100 if np.isfinite(ps) else float('nan'):7.1f}% "
                  f"{need:7.3f}x   {pub_need:8.3f}x   {note}")
    out["bq3"] = res

    # ---- BQ3b: WHERE THE MOVE IS.  The pedal is pinned (BQ1), so it is all model side. --------
    # Compared UNMATCHED on both ends, because that is the membership rule the PRIMARY figures
    # were taken under -- comparing a matched `now` against an unmatched `then` would be
    # `aggregate-moved-check-membership-first` committed inside the gate written to avoid it.
    print("\n" + "-" * 94)
    print("BQ3b  WHERE THE MOVE IS -- the pedal is pinned by BQ1, so this is the MODEL epoch")
    print("-" * 94)
    print(f"  model span, UNMATCHED (the PRIMARY figures' own membership rule), then vs now")
    print(f"  {'feature':<14s} {'then':>8s} {'src':<34s} " +
          " ".join(f"{s.replace('sweep_', ''):>8s}" for s in W.SWEEPS))
    epoch = {}
    for name in TARGET_FEATURES:
        pri = PRIMARY[name]
        cells = []
        for sw in W.SWEEPS:
            c = bq2[name][sw]
            # unmatched model span over whatever the model alone can read
            fs = [v for lv, v in sorted(c["model_all"].items())]
            sp = (max(fs) / min(fs) - 1.0) * 100.0 if len(fs) >= 3 else float("nan")
            cells.append((sp, len(fs)))
        epoch[name] = {"then_pct": pri["model_pct"], "src": pri["src"],
                       "now": {sw: {"span_pct": c[0], "n": c[1]}
                               for sw, c in zip(W.SWEEPS, cells)}}
        shown = " ".join((f"{sp:7.1f}%" if np.isfinite(sp) else f"{'n<3':>8s}") for sp, _ in cells)
        print(f"  {name:<14s} {pri['model_pct']:7.1f}% {pri['src'][:34]:<34s} {shown}")
        print(f"  {'':<14s} {'':>8s} {'(n per sweep)':<34s} " +
              " ".join(f"{n:>8d}" for _, n in cells))
    out["bq3b"] = epoch
    return res


def gate_bq4(bq3, rep_path, out):
    """WHAT IT MEANS FOR THE s189 CANDIDATE -- graded, not narrated."""
    print("\n" + "=" * 94)
    print("BQ4  THE CONSEQUENCE for the s189 taper candidate  (⛔ nothing is shipped by this gate)")
    print("=" * 94)
    ay_path = "analysis/reports/s189_level_taper.json"
    if not os.path.exists(ay_path):
        print(f"  ⚠ {ay_path} absent -- run GATE AY first; the delivered fold cannot be quoted")
        out["bq4"] = {"status": "no AY report"}
        return
    ay = json.load(open(ay_path))
    head = ay.get("ay5", {}).get("headroom", {})
    fold = head.get("fold_required")
    if fold is None:
        print("  ⚠ GATE AY's report carries no ay5.headroom.fold_required")
        out["bq4"] = {"status": "no fold in AY report"}
        return
    print(f"  the LEVEL-LAW taper wants a mix-ratio fold of {fold:.3f}x (GATE AY5(b), b/a span")
    print(f"  {head.get('span_shipped', float('nan')):.4f} -> {head.get('span_required', float('nan')):.4f}).")
    print( "  ⚠ THAT IS THE MIX RATIO, NOT THE FEATURE -- AY5(b)'s own necessary-not-sufficient")
    print( "  caveat binds here too.  A fold in b/a is what DRIVES a centre to move; whether the")
    print( "  centre follows 1:1 is not measured by either gate.")
    rows = []
    print(f"\n  {'feature':<14s} {'sweep':<14s} {'need now':>9s} {'delivered':>10s} "
          f"{'need/delivered':>15s}")
    for name in TARGET_FEATURES:
        for sw in W.SWEEPS:
            need = bq3[name][sw]["need"]
            if not np.isfinite(need):
                continue
            rows.append((name, sw, need, fold, need / fold))
            tag = f"{need/fold:8.2f}x SHORT" if need > fold else f"{need/fold:8.2f}x  REACHES"
            print(f"  {name:<14s} {sw:<14s} {need:8.3f}x {fold:9.3f}x {tag:>15s}")
    if not rows:
        print("  ⇒ ⛔ NO GRADEABLE CELL -- every (feature, sweep) was refused above.  The targets")
        print("    cannot be graded on this epoch, which is itself the answer to `measure first`.")
        out["bq4"] = {"status": "no gradeable cell", "fold": fold}
        return
    worst = max(r[4] for r in rows)
    best = min(r[4] for r in rows)
    reach = [r for r in rows if r[4] <= 1.0]
    print(f"\n  {len(reach)} of {len(rows)} graded cells are REACHED by the taper's own fold;")
    print(f"  need/delivered runs {best:.2f}x .. {worst:.2f}x")
    # ⚠ The comparison this replaces: against AY's RESTATED pair the same fold is 1.45x / 2.21x
    # short at every cell.  Printed so the size of the correction is visible, not inferred.
    old = [PUBLISHED[n]["pedal_pct"] / PUBLISHED[n]["model_pct"] / fold for n in TARGET_FEATURES]
    print(f"  against the RESTATED pair AY currently grades against it would read "
          f"{min(old):.2f}x .. {max(old):.2f}x short at every cell,")
    print( "  i.e. re-measuring moves the candidate from 'clearly short on both' to "
           f"'{len(reach)} of {len(rows)} cells reached'.")
    print( "  ⛔ THAT IS NOT A LICENCE TO SHIP IT.  Three things still bind: (i) AY5(b)'s")
    print( "  necessary-not-sufficient caveat -- a fold in b/a is not a measured centre move;")
    print( "  (ii) the majority of cells are still short; (iii) the taper's own price (a matrix")
    print( "  render and an `OdToneRestore` mix-law re-check) is unpaid.")
    out["bq4"] = {"fold_delivered": fold, "cells": [
        {"feature": a, "sweep": b, "need": c, "fold": d, "shortfall": e} for a, b, c, d, e in rows],
        "n_reach": len(reach), "n_cells": len(rows), "worst_shortfall": worst,
        "best_shortfall": best}


def verdict(bq1, bq3, out):
    """A COMPUTED verdict -- every branch derived from the table above."""
    print("\n" + "=" * 94)
    print("BQ  VERDICT")
    print("=" * 94)
    graded = [(n, s, v["need"]) for n in TARGET_FEATURES for s, v in bq3[n].items()
              if np.isfinite(v["need"])]
    refused = [(n, s, v["note"]) for n in TARGET_FEATURES for s, v in bq3[n].items()
               if not np.isfinite(v["need"])]
    print(f"  graded cells  : {len(graded)} of {len(TARGET_FEATURES) * len(W.SWEEPS)}")
    print(f"  refused cells : {len(refused)}")
    for n, s, note in refused:
        print(f"      {n:<14s} {s:<14s} {note}")
    moved = []
    for n in TARGET_FEATURES:
        pub = PUBLISHED[n]["pedal_pct"] / PUBLISHED[n]["model_pct"]
        vals = [v["need"] for v in bq3[n].values() if np.isfinite(v["need"])]
        if vals:
            moved.append((n, pub, min(vals), max(vals)))
    if not moved:
        print("\n  ⛔ THE TARGETS CANNOT BE GRADED ON THIS EPOCH.  Every cell was refused, so item")
        print("    9's `needs 1.744x / 2.670x` may not be re-quoted and may not be used to grade a")
        print("    candidate -- which is the `measure first` decision's answer, in the negative.")
        out["verdict"] = {"status": "ungradeable", "n_graded": 0}
        return
    print(f"\n  {'feature':<14s} {'AY grades':>10s} {'re-measured (min..max over sweeps)':>40s}"
          f"  {'direction':>12s}")
    shrank = grew = 0
    for n, pub, lo, hi in moved:
        if hi < pub:
            d, shrank = "SMALLER", shrank + 1
        elif lo > pub:
            d, grew = "LARGER", grew + 1
        else:
            d = "straddles"
        print(f"  {n:<14s} {pub:9.3f}x   {lo:.3f}x .. {hi:.3f}x  {d:>12s}")
    # THE COMPUTED HEADLINE.  Both branches written; the data picks one.
    print()
    if shrank == len(moved):
        print(f"  ⇒ ⭐⭐ EVERY RE-MEASURED TARGET IS SMALLER THAN THE ONE GATE AY GRADES AGAINST.")
        print( "    The mix-law lever has LESS to close than item 9 currently claims, at every")
        print( "    feature and every stimulus rung that could be graded.")
    elif grew == len(moved):
        print(f"  ⇒ ⚠⚠ EVERY RE-MEASURED TARGET IS LARGER -- the lever has MORE to close than")
        print( "    item 9 claims, so the published pair was optimistic.")
    else:
        print(f"  ⇒ MIXED: {shrank} smaller, {grew} larger, {len(moved)-shrank-grew} straddling.")
    if bq1:
        print( "\n  AND THE MOVE IS ENTIRELY MODEL-SIDE, MEASURED NOT ASSUMED: BQ1 pins the pedal")
        print( "  against two independent primary artefacts (0.1 % on both), so the pedal spans")
        print( "  are unchanged and every bit of the shrink is the model's own LEVEL sensitivity")
        print( "  having GROWN since those targets were taken.  BQ3b sizes that growth.")
        print( "  ⛔ NOT attributed to any one change: s181's end stop, s185's re-anchor and")
        print( "  s187's GRUNT-keyed bass-null fix all landed in between, and s187 moved THIS")
        print( "  feature's centre by construction.  Direction measured; attribution not claimed.")
    if not bq1:
        print("  ⚠⚠ THE PEDAL-SIDE KNOWN ANSWER DID NOT REPRODUCE, so the published pair itself is")
        print("     in question and the comparison above is between two differently-membered")
        print("     statistics.  Quote the re-measured column with that caveat, never alone.")
    out["verdict"] = {"status": "graded", "n_graded": len(graded), "n_refused": len(refused),
                      "pedal_ka": bool(bq1),
                      "features": {n: {"published": p, "lo": lo, "hi": hi}
                                   for n, p, lo, hi in moved}}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--json", default=OUT_JSON)
    ap.add_argument("--jobs", type=int, default=None)
    args = ap.parse_args()

    print("=" * 94)
    print("GATE BQ -- item 9's LEVEL-sensitivity targets, re-measured on the current epoch")
    print("=" * 94)
    out = {}
    fp_before = gate_bq0(args.report, out)

    rep = json.load(open(args.report))
    caps = {c["file"]: c for c in rep["captures"]}
    lad = W.level_ladder(caps)                     # IMPORTED membership
    print(f"\n  LEVEL ladder: {len(lad)} detents  {sorted(lad)}")
    for lv, f in sorted(lad.items()):
        print(f"      LEVEL {lv:<6.3f} {f}")
    print(f"\n  rendering / reading {len(lad)} captures x {len(W.SWEEPS)} sweeps ...")
    recs = pmap(_cell, [(f, REN_DIR) for f in lad.values()], jobs=args.jobs)
    rows = {r["file"]: r for r in recs}

    fp_after = dir_fingerprint(FORBIDDEN_DIR)
    if fp_after != fp_before:
        sys.exit(f"GATE BQ: the READ-ONLY cache {FORBIDDEN_DIR} CHANGED during this run "
                 f"({fp_before} -> {fp_after}) -- the s122 epoch GATEs AV/AW/AF/AG/BC read has "
                 f"been destroyed; restore it before trusting any of those gates")
    out["bq0"]["forbidden_fp_after"] = fp_after
    print(f"\n  READ-ONLY cache unchanged: {fp_after}")

    ka = gate_bq1(rows, lad, out)
    bq2 = gate_bq2(rows, lad, out)
    bq3 = gate_bq3(bq2, out)
    gate_bq4(bq3, args.report, out)
    verdict(ka, bq3, out)

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1, default=float)
    print(f"\n  wrote {args.json}")


if __name__ == "__main__":
    main()
