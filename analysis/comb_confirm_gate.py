#!/usr/bin/env python3.11
"""GATE BV -- THE FINAL CONFIRMATION SWEEP.  Action-list item (10), USER-ADDED 2026-08-09.

WHY THIS EXISTS.  Open item 19 (the full notch/peak review, P1-P5, complete at s190) measured the
alternating notch/peak comb that is this pedal's whole voice -- but it did so **on one instrument,
at one epoch**, and it produced a seven-row table (N1/P1/N2/P2/N3/P3/N4) that is a SNAPSHOT rather
than a standing guarantee.  Everything shipped since moved the model underneath it:

    s185  kMixCf[0]                    s195  odMakeupHfPeakDbNonCut
    s187  clipC15Cut / LowCutDbCut     s196  kNotchMixK  Flat + Boost rows
    s190  the LEVEL taper              s199  kNotchMixK  Cut row, entries 0 and 2

This gate re-runs the comb measurement at the END, on the shipped build, to answer two questions
item 19's own table cannot: **did anything regress**, and **does every fix survive OFF the setting
it was fitted at**.  ⛔ It changes no constant and proposes none.  Its output is a table.

⛔⛔ ITS WHOLE POINT IS MEMBERSHIP, SO IT MUST NOT BE BLEED-FREE-ONLY.  Three independent findings
say a bleed-free-only confirmation would confirm the one setting the user has explicitly said is
not the reference, on an axis where two of the three do not transfer:

  * s173's USER STEER -- "ONLY looking at bleed free for literally anything breaks ANY setting that
    isn't level1700 ... `ref-od` should be the starting reference, NEVER the bleed free one."  Said
    about a correction that CHANGES SIGN across the mix (+4.53 dB too bright bleed-free against
    0.7-3.3 dB too dark at every played setting).
  * s186's BO2 -- the GRUNT ordering measured bleed-free does not survive the mix: 0 of 3 readable
    sweeps agree, and the argmax MOVES (bleed-free says flat is worst, the mix says boost).
  * s191's AP1b -- the area estimator's censoring robustness, the property GATE AP's whole remedy
    rests on, is 4.1x at the corner and **1.0x at all 12 mixed cells**.

REQUIRED COVERAGE, ALL FOUR AXES AT ONCE, and BV1 asserts each of them:
    (a) MIX       the bleed-free corner AND `ref-od` AND the LEVEL and BLEND ladders
    (b) STIMULUS  all four rungs -- `W.SWEEPS` gives them free, INCLUDING `drv_-12` (the user's
                  stated playing level) and `drv_-6`
    (c) GRUNT     all three positions, never Cut alone (s151: every untokened capture is Cut)
    (d) DRIVE     the whole ladder, not its endpoints (s129: an endpoint pair is not a ladder)

FOUR ESTIMATOR RULES BIND THIS GATE.  Each is a defect this project has already paid for once, and
each produces a plausible-looking NUMBER rather than an error:

  1. QUOTE CLASSIFICATIONS, NOT PERCENTAGES (s158 GATE AV, s159 GATE AW).  Every FIXED /
     DRIVE-DEPENDENT verdict is window-stable on both sides (0 of 7 pedal, 0 of 4 model flip) and
     the SIZES move by up to 28.4 %.  So every verdict line here is a computed classification and
     the percentages beside it are printed as context, never as the finding.
  2. GRADE DEPTH AT A MIXED SETTING, NEVER GAIN (s192 AP3b).  `d(depth)/d(gain)` is 0.890
     bleed-free and 0.299 at the mix, so a gain-unit bar is ~3.3x too tight there.  This gate
     grades DEPTH only; it solves for no gain anywhere.
  3. PRINT BOTH THE POINT AND THE AREA DEPTH (s152 GATE AP, s180 BJ0d).  The point depth is a
     LOWER BOUND wherever the null bottom sits at or below the deconvolution residue.  Both are
     computed for every reading and both are printed; neither is allowed to stand alone.
  4. MATCH MEMBERSHIP BEFORE DIFFERENCING (s159 AW5, the twelfth occurrence).  An estimator that
     REFUSES is correlated with the thing being graded, so every model-vs-pedal comparison here is
     over cells readable on BOTH sides, and the drops are NAMED.

⚠ AND REFUSALS ARE AN EXPECTED OUTPUT, NOT MISSING DATA.  s184 measured `bass_notch` and
`treble_notch` resolving in **0 of 36** bleed-free readings against 255 and 347 of 684 played: they
are MIX features and a bleed-free reading is structurally blind to them.  BV3 reports the refusal
census as a finding about the membership.  A sweep that reports those as gaps has mis-read itself.

THE DEPTH ESTIMATOR IS THE COMB'S OWN CONTRAST, and it is chosen rather than invented.  The seven
features alternate notch/peak/notch/..., so each one's natural shoulders are its NEIGHBOURS, and
the contrast to them is exactly the quantity item 18/19 already grade as `C1 = mid_peak -
mid_notch` (s172, s179).  ⛔ It is NOT `locate()`'s `prom`: GATE AU (s157) proved that statistic's
turn-back test is unreachable code and GATE AV/AW (s158/s159) that it MIXES DEPTH WITH WIDTH and is
a DETECTOR only.  `prom` is still used here for exactly what it is good for -- deciding whether a
feature is PRESENT -- and never as a height.

⛔⛔ THIS GATE MUST NOT TOUCH `build/s122_feature_locus/`.  That cache is READ-ONLY and ENFORCED
(s159): GATEs AV / AW / AF / AG / BC all read the epoch it holds and its stamps are already stale
against the current binary, so pointing any `ren_dir` at it would re-render all 25 and destroy it.
BV0 fingerprints it before and after and REFUSES on any change.

Run:
    python3.11 analysis/comb_confirm_gate.py [--report analysis/reports/s199_cutmixk.json]
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
import feature_locus_gate as W     # noqa: E402  -- locator, windows, grid, constants: IMPORTED
import od_tone_restore_fit as F    # noqa: E402  -- SETS membership + the AREA depth convention
from parallel import pmap          # noqa: E402

OUT_JSON = "analysis/reports/s201_comb_confirm.json"
REN_DIR = "build/s201_comb_confirm"        # PRIVATE.  Never W.REN_DIR.
FORBIDDEN_DIR = W.REN_DIR                  # build/s122_feature_locus -- READ-ONLY, ENFORCED
DEFAULT_REPORT = "analysis/reports/s199_cutmixk.json"

# ---- MEMBERSHIP -------------------------------------------------------------------------------
# The base is `od_tone_restore_fit.SETS`' 14 groups, named by the item as "the ready-made
# membership" -- 43 unique captures spanning LEVEL (9 detents), BLEND (5), DRIVE (5 rungs), GRUNT
# (3) and the LEVEL x BLEND interior.  IMPORTED, so it cannot drift from the tool that defines it.
#
# ⭐ PLUS SIX CAPTURES THAT ARE ON DISK AND THAT `SETS` DOES NOT HOLD (`check-for-unread-data-first`,
# tenth occurrence).  `SETS`' GRUNT coverage at a MIX is 3 cells wide (`grunt_mix`), and s195
# measured what an unbalanced GRUNT pool does to a conclusion on this exact comb: its condition
# list was 7 cut / 1 flat / 2 boost, and the pooled statistic built on it cancelled a sign change
# and reported a number no condition had.  These six are the flat/boost twins of the `blend` group
# -- the BLEND ladder at the two GRUNT positions the mixed sets otherwise reach only at BLEND max.
# ⚠ They are ADDITIVE and change no frozen group; `SETS` itself is untouched by this gate.
EXTRA_MIXED_GRUNT = (
    "grunt-flat_blend-1430_base-od.wav",
    "grunt-flat_blend-1200_base-od.wav",
    "grunt-flat_blend-0930_base-od.wav",
    "grunt-boost_blend-1430_base-od.wav",
    "grunt-boost_blend-1200_base-od.wav",
    "grunt-boost_blend-0930_base-od.wav",
)

# ---- the bars, every one IMPORTED or DERIVED ---------------------------------------------------
# The locator's own resolution, in W's convention (`GRID_STEP_FRAC / 3`) -- the figure s158/s159
# use as the bar below which a centre movement is not resolved.
RESOLUTION_FRAC = W.GRID_STEP_FRAC / 3.0
# A centre error must clear the resolution by this multiple before it is called an OFFSET rather
# than TRACKS.  ⚠ Not a fit bar: it is the point below which this instrument cannot tell the two
# sides apart, so calling anything under it a defect would be reading noise.
CENTRE_MULT = 3.0
# A depth error must clear the fit's own residual before it is called a defect.  IMPORTED from the
# stage that owns this comb: s151's converged fit residual, the bar s185/s190 both grade against.
DEPTH_TOL_DB = 0.83
# The clean fraction at the bleed-free corner is the shipped end stop -- DERIVED through the same
# resolver every other tool uses, never transcribed (s182's single-resolver pattern).
CORNER_CF_TOL = 1e-6
# ⚠⚠ A CELL THINNER THAN THIS CARRIES NO VERDICT.  `check-n-before-reading-a-trend` (s82): the
# first run of this gate quoted `+18.33 dB` off a SINGLE matched cell and `+4.49` off two, in the
# same table as figures backed by 50.  A thin cell is still PRINTED -- it is a real reading and
# suppressing it would hide membership -- but it is labelled THIN and no verdict is drawn from it.
MIN_N = 3


# =================================================================================================
def dir_fingerprint(d):
    """Content fingerprint of a render directory -- what BV0 asserts does not move."""
    if not os.path.isdir(d):
        return "ABSENT"
    h = hashlib.sha256()
    for p in sorted(glob.glob(os.path.join(d, "*"))):
        st = os.stat(p)
        h.update(os.path.basename(p).encode())
        h.update(str((st.st_size, st.st_mtime_ns)).encode())
    return h.hexdigest()[:16]


def _render_into(out, args):
    """W.render, but into THIS gate's directory, with the read-only cache refused by assertion."""
    assert not os.path.abspath(out).startswith(os.path.abspath(FORBIDDEN_DIR)), \
        f"GATE BV: refusing to render into the READ-ONLY cache {FORBIDDEN_DIR}"
    return W.render(out, args)


def valid(r):
    """W3's own validity rule, applied to every reading this gate quotes.

    A centre resting ON a window bound is a REFUSAL, not a measurement (s151), and a feature under
    the prominence bar is not established PRESENT (s126/s133 -- an extremum finder always returns
    something).  ⚠ `prom` decides PRESENCE here and nothing else; it is never read as a height."""
    return (not r["edge"]) and r["margin_frac"] >= W.EDGE_MARGIN_FRAC and r["prom"] >= W.MIN_PROM_DB


def shoulder_ok(r):
    """A neighbour used as a DEPTH REFERENCE need not be a resolved feature -- it only has to be a
    measured level.  What disqualifies it is resting on a window BOUND, where its value is the
    bound rather than the curve's own local extremum."""
    return (not r["edge"]) and r["margin_frac"] >= W.EDGE_MARGIN_FRAC


def comb_of(al, sw, ref):
    """Locate all seven features on ONE side of one (capture, sweep) cell, with BOTH depths.

    The curve, the grid, the smoothing and the locator are all W's; what this adds is the AREA
    reading at each located centre, through `F.band_db_grid` -- GATE R's own 1/6-octave
    power-integrated convention, IMPORTED rather than re-derived (s149: a shared helper is what
    keeps five gates from drifting apart, and re-implementing one is how they start)."""
    f, m = A.transfer_h1(A.seg_of(al, sw), ref)
    d = W.smooth(f, m)
    out = {"floor_db": W.floor_db(f, m)}
    for name, kind, win, _lab in W.FEATURES:
        r = W.locate(d, win, kind)
        r["area_db"] = F.band_db_grid(W.GRID, d, r["f0"])
        r["floor_margin_db"] = r["value"] - out["floor_db"]
        out[name] = r
    # ---- the comb CONTRAST, both estimators ----------------------------------------------------
    # Each feature is referred to its NEIGHBOURS in the comb, which is the quantity item 18/19
    # already grade (`C1 = mid_peak - mid_notch`).  Sign convention: POSITIVE = the feature is
    # deep (a notch) or tall (a peak), i.e. more contrast is a larger number on both kinds.
    names = [n for n, _k, _w, _l in W.FEATURES]
    for i, (name, kind, _win, _lab) in enumerate(W.FEATURES):
        nb = [names[j] for j in (i - 1, i + 1) if 0 <= j < len(names)]
        usable = [n for n in nb if shoulder_ok(out[n])]
        rec = out[name]
        if not usable:
            rec["depth_point"] = rec["depth_area"] = None
            rec["shoulders"] = []
            continue
        sgn = 1.0 if kind == "min" else -1.0
        rec["shoulders"] = usable
        rec["depth_point"] = sgn * (float(np.mean([out[n]["value"] for n in usable])) - rec["value"])
        rec["depth_area"] = sgn * (float(np.mean([out[n]["area_db"] for n in usable])) - rec["area_db"])
    return out


def _cell(args):
    """One capture -> the comb on BOTH sides at all four stimulus rungs."""
    fname, ren_dir = args
    orig, ref = W._load_orig()
    parsed = C.parse_capture(fname)
    ra = C.render_args(parsed)
    out = os.path.join(ren_dir, fname.replace(".wav", "") + "_plugin.wav")
    _render_into(out, ra)
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    rec = {"file": fname, "settings": parsed, "cf": F.clean_frac_of(fname), "model": {}, "pedal": {}}
    for sw in W.SWEEPS:
        rec["model"][sw] = comb_of(ren_al, sw, ref)
        rec["pedal"][sw] = comb_of(cap_al, sw, ref)
    return rec


# ---- small shared readers ----------------------------------------------------------------------
GRUNT_NAME = {0: "boost", 1: "cut", 2: "flat"}


def grunt_of(rec):
    return GRUNT_NAME.get(rec["settings"].get("gruntIdx"), "?")


def is_corner(rec, corner_cf):
    return abs(rec["cf"] - corner_cf) <= CORNER_CF_TOL


def med(xs):
    return float(np.median(xs)) if len(xs) else float("nan")


def refusal_reason(r):
    """WHY a reading was refused -- and the distinction is load-bearing, not bookkeeping.

    `EDGE`/`MARGIN` mean the extremum sits on or near a window BOUND: the window no longer contains
    the feature, which is a statement about where the feature MOVED TO (s151 -- a minimum on a bound
    is a refusal, and s179 measured the model's composite ~320 Hz notch wandering 20.7 % across
    GRUNT, i.e. onto its window's edges).  `PROM` means the window is right and there is no feature
    in it -- s126/s133's presence/absence result.  Reporting both as one number would merge
    "the feature moved" with "the feature is gone", which are different findings with different
    owners."""
    if r["edge"]:
        return "EDGE"
    if r["margin_frac"] < W.EDGE_MARGIN_FRAC:
        return "MARGIN"
    if r["prom"] < W.MIN_PROM_DB:
        return "PROM"
    return None


SHORT = {"TRACKS": "TRK", "OFFSET model HIGH": "HIGH", "OFFSET model LOW": "LOW",
         "MATCHES": "OK", "model TOO DEEP/TALL": "DEEP", "model TOO SHALLOW/FLAT": "SHAL",
         None: "-", "REFUSED": "REF"}


def short(v):
    """Compact verdict code for the per-rung stability line.

    ⚠⚠ THIS EXISTS BECAUSE A LOSSY DISPLAY HID A SIGN CHANGE IN THIS GATE'S OWN FIRST RUN.  The
    per-rung line truncated every verdict to 6 characters, so `OFFSET model HIGH` and `OFFSET model
    LOW` both printed as `OFFSET` -- and a cell whose direction INVERTS across the stimulus ladder
    read as four identical rungs beside a NOT-STABLE flag, i.e. as a contradiction rather than as
    the finding.  That is s195's defect exactly (a signed statistic collapsed until a sign change
    cancelled) arriving through a format string.  Every code here is direction-preserving."""
    return SHORT.get(v, str(v)[:4])


def verdict_stable(per_sweep):
    """Does a pooled verdict survive being split by stimulus rung?

    ⛔ THE STIMULUS AXIS MUST NOT BE POOLED SILENTLY.  s178 measured this comb's treble null reading
    13.56 / 4.93 / 2.35 dB on ND and 2.58 / 24.78 / 6.83 on one model build across three adjacent
    rungs -- "20 dB too deep" and "11 dB too shallow" were the SAME BUILD two rungs apart.  A median
    over the ladder hides exactly that, so every pooled verdict here is re-computed per rung and
    flagged when the rungs do not agree."""
    vs = {v for v in per_sweep.values() if v is not None}
    return len(vs) <= 1


# =================================================================================================
def gate_bv0(rep_path, out):
    """PROVENANCE -- the binary IS the shipped build, and the read-only cache is untouched."""
    print("\n" + "=" * 96)
    print("BV0  PROVENANCE -- binary epoch, report epoch, and the READ-ONLY s122 cache")
    print("=" * 96)
    binp = CR.DEFAULT_BIN
    if not os.path.exists(binp):
        sys.exit(f"GATE BV0: render binary {binp} is absent -- nothing below can be rendered")
    bmt = os.stat(binp).st_mtime
    newer = [p for p in glob.glob("src/**/*", recursive=True)
             if os.path.isfile(p) and os.stat(p).st_mtime > bmt]
    md5 = hashlib.md5(open(binp, "rb").read()).hexdigest()
    print(f"  render binary   : {binp}")
    print(f"  md5             : {md5}")
    print(f"  src files newer : {len(newer)}")
    if newer:
        # s152/s185: a stale binary reports the PREVIOUS build's numbers with no error anywhere.
        sys.exit(f"GATE BV0: {len(newer)} src file(s) postdate the render binary ({newer[:3]}) -- "
                 f"rebuild first, or every model-side number below is the previous build's")
    if not os.path.exists(rep_path):
        sys.exit(f"GATE BV0: report {rep_path} is absent -- it supplies the LEVEL ladder membership")
    fp = dir_fingerprint(FORBIDDEN_DIR)
    stamps = glob.glob(os.path.join(FORBIDDEN_DIR, "*.args.json"))
    n_stale = sum(1 for p in stamps if json.load(open(p)).get("bin") != W._bin_sig())
    print(f"  report          : {rep_path}")
    print(f"  READ-ONLY cache : {FORBIDDEN_DIR}  fingerprint {fp}")
    print(f"                    {n_stale} of {len(stamps)} stamps STALE against this binary -- which")
    print( "                    is exactly why nothing here may render into it (s159/s188)")
    print(f"  private renders : {REN_DIR}")
    out["bv0"] = {"bin": binp, "md5": md5, "src_newer": len(newer), "report": rep_path,
                  "forbidden_dir": FORBIDDEN_DIR, "forbidden_fp_before": fp,
                  "forbidden_stale_stamps": n_stale, "ren_dir": REN_DIR}
    return fp


def build_membership(rep_path, out):
    """The four-axis capture set, assembled and then ASSERTED (BV1)."""
    # ⚠ Keyed by FILE exactly as GATE W's own `main()` does it (line 836) -- the report stores a
    # LIST, and `level_ladder` takes the dict.  Re-keyed here rather than re-implemented.
    caps = {c["file"]: c for c in json.load(open(rep_path))["captures"]}
    ladder = W.level_ladder(caps)                     # resolved by SETTINGS, not by filename
    base = sorted({fn for rows in F.SETS.values() for fn, _d in rows})
    extra = [f for f in EXTRA_MIXED_GRUNT]
    files = sorted(set(base) | set(extra) | set(ladder.values()))
    missing = [f for f in files if not os.path.exists(os.path.join(C.CAPTURE_DIR, f))]
    if missing:
        sys.exit(f"GATE BV1: {len(missing)} capture(s) in the membership are absent: {missing[:4]}")
    out["_ladder"] = {str(k): v for k, v in ladder.items()}
    return files, ladder, base, extra


def gate_bv1(rows, base, extra, ladder, out):
    """MEMBERSHIP, ASSERTED -- all four axes, with the asymmetries NAMED as capture facts."""
    print("\n" + "=" * 96)
    print("BV1  MEMBERSHIP -- the four axes, asserted rather than intended")
    print("=" * 96)
    ax = {"grunt": {}, "drive": {}, "level": {}, "blend": {}}
    for r in rows:
        s = r["settings"]
        ax["grunt"].setdefault(grunt_of(r), []).append(r["file"])
        for k in ("drive", "level", "blend"):
            ax[k].setdefault(round(float(s.get(k, -1)), 3), []).append(r["file"])
    print(f"  captures         : {len(rows)}  "
          f"({len(base)} from od_tone_restore_fit.SETS' {len(F.SETS)} groups, "
          f"+{len(set(extra) - set(base))} mixed-GRUNT already on disk, "
          f"+{len(set(ladder.values()) - set(base) - set(extra))} from the LEVEL ladder)")
    print(f"  stimulus rungs   : {len(W.SWEEPS)}  {list(W.SWEEPS)}   (every capture carries all four)")
    for k in ("grunt", "drive", "level", "blend"):
        items = sorted(ax[k].items(), key=lambda kv: str(kv[0]))
        print(f"  {k:14s}   : {len(items)} distinct -- " +
              ", ".join(f"{a}:{len(b)}" for a, b in items))
    fails = []
    if len(ax["grunt"]) < 3:
        fails.append(f"GRUNT has {len(ax['grunt'])} of 3 positions -- s151's trap is live")
    if len(ax["drive"]) < 5:
        fails.append(f"DRIVE has {len(ax['drive'])} rungs -- s129, an endpoint pair is not a ladder")
    if len(ax["level"]) < 5:
        fails.append(f"LEVEL has {len(ax['level'])} detents -- the MIX axis is not covered")
    if len(ax["blend"]) < 4:
        fails.append(f"BLEND has {len(ax['blend'])} positions -- the OTHER mix axis is not covered")
    if fails:
        sys.exit("GATE BV1 REFUSES:\n  " + "\n  ".join(fails))
    ng = {g: len(v) for g, v in ax["grunt"].items()}
    print("\n  ✅ all four axes covered.  ⚠ AND THE GRUNT POOL IS UNBALANCED BY CONSTRUCTION: "
          f"{ng} --")
    print( "     every capture without a `grunt-` token is GRUNT = CUT (s151), so a cut-heavy pool is")
    print( "     a property of the capture set, not a choice.  ⇒ EVERY statistic below is computed")
    print( "     WITHIN a GRUNT position and never pooled across them (s195: a pooled median over")
    print( "     this axis cancelled a sign change and reported a number no condition had).")
    out["bv1"] = {"n_captures": len(rows), "sweeps": list(W.SWEEPS),
                  "grunt": ng, "drive": {str(k): len(v) for k, v in ax["drive"].items()},
                  "level": {str(k): len(v) for k, v in ax["level"].items()},
                  "blend": {str(k): len(v) for k, v in ax["blend"].items()}}


def gate_bv2(rows, ladder, out):
    """KNOWN ANSWER -- the PEDAL side is binary-independent, so it must reproduce GATE BQ.

    Nothing this project has shipped can move a pedal capture, so the pedal's LEVEL-ladder spans
    must still be what s190's GATE BQ measured -- and BQ's own BQ1 established that those figures
    reproduce s125's published loci and GATE AE's docstring to ~0.1 %.  If they reproduce here, the
    locator, the windows, the ladder membership and the matching rule are validated together, and
    every model-side move below is attributable to the MODEL epoch alone (s159 AW1b's trick)."""
    print("\n" + "=" * 96)
    print("BV2  KNOWN ANSWER -- the pedal side cannot have moved, so it must reproduce GATE BQ")
    print("=" * 96)
    bq_path = "analysis/reports/s190_level_sensitivity.json"
    if not os.path.exists(bq_path):
        # `empty-gate-must-fail`: a known answer whose reference is absent must REFUSE, not skip.
        sys.exit(f"GATE BV2: {bq_path} is absent -- the only binary-independent cross-epoch check "
                 f"this gate has.  Re-run GATE BQ, or run with --no-ka and say so in the write-up.")
    bq = json.load(open(bq_path))["bq1"]
    by_file = {r["file"]: r for r in rows}
    ok = True
    res = {}
    sw = bq["sweep"]
    for feat, blk in bq["features"].items():
        detents = [float(x) for x in blk["detents"]]
        f0 = []
        for lv in detents:
            fn = ladder.get(lv)
            if fn is None or fn not in by_file:
                f0 = []
                break
            f0.append(by_file[fn]["pedal"][sw][feat]["f0"])
        if not f0:
            sys.exit(f"GATE BV2: cannot rebuild GATE BQ's {feat} ladder from this membership")
        span = 100.0 * (max(f0) / min(f0) - 1.0)
        want = blk["measured_pedal_pct"]
        rel = abs(span - want) / want
        good = rel <= 0.01
        ok &= good
        res[feat] = {"measured_pct": span, "bq_pct": want, "rel_err": rel, "n": len(f0),
                     "reproduces": bool(good)}
        print(f"  {feat:13s} pedal span over {len(f0)} detents at {sw}: "
              f"{span:7.3f} %  vs GATE BQ's {want:7.3f} %   rel err {rel:.2e}  "
              f"{'✅' if good else '❌'}")
    print(f"\n  ⭐ GATE BQ's own BQ1 established these reproduce s125's published loci (42.78 %) and")
    print( "     GATE AE's docstring (44.1 %), so agreeing with BQ chains this gate to TWO earlier")
    print( "     sessions' artefacts on an instrument none of them shares.")
    if not ok:
        sys.exit("GATE BV2 REFUSES: the pedal side does not reproduce -- the difference is this "
                 "gate's membership or locator, NOT the pedal, and nothing below is attributable.")
    out["bv2"] = {"sweep": sw, "features": res, "all_reproduce": True}


def gate_bv3(rows, corner_cf, out):
    """REFUSALS -- a census, reported as a finding about the membership rather than as gaps."""
    print("\n" + "=" * 96)
    print("BV3  REFUSAL CENSUS -- where each feature can be READ at all, by mix class")
    print("=" * 96)
    print("  s184 measured `bass_notch` and `treble_notch` resolving in 0 of 36 BLEED-FREE readings")
    print("  against 255/347 of 684 played: they are MIX features and a bleed-free read is blind to")
    print("  them.  A gate that reports that as missing data has mis-read its own membership.\n")
    print(f"  {'feature':14s} {'corner model':>13s} {'corner pedal':>13s} "
          f"{'played model':>13s} {'played pedal':>13s}   {'matched':>9s}")
    cens = {}
    for name, _k, _w, _l in W.FEATURES:
        cnt = {("corner", "model"): [0, 0], ("corner", "pedal"): [0, 0],
               ("played", "model"): [0, 0], ("played", "pedal"): [0, 0]}
        why = {("corner", "model"): {}, ("corner", "pedal"): {},
               ("played", "model"): {}, ("played", "pedal"): {}}
        matched = [0, 0]
        for r in rows:
            cls = "corner" if is_corner(r, corner_cf) else "played"
            for sw in W.SWEEPS:
                mv = valid(r["model"][sw][name])
                pv = valid(r["pedal"][sw][name])
                for side, ok, rec in (("model", mv, r["model"][sw][name]),
                                      ("pedal", pv, r["pedal"][sw][name])):
                    cnt[(cls, side)][0] += ok
                    cnt[(cls, side)][1] += 1
                    if not ok:
                        k = refusal_reason(rec)
                        why[(cls, side)][k] = why[(cls, side)].get(k, 0) + 1
                matched[0] += (mv and pv)
                matched[1] += 1
        cens[name] = {f"{c}_{s}": cnt[(c, s)] for c, s in cnt}
        cens[name]["matched"] = matched
        cens[name]["why"] = {f"{c}_{s}": why[(c, s)] for c, s in why}
        f = lambda t: f"{t[0]:4d}/{t[1]:<4d}"  # noqa: E731
        print(f"  {name:14s} {f(cnt[('corner','model')]):>13s} {f(cnt[('corner','pedal')]):>13s} "
              f"{f(cnt[('played','model')]):>13s} {f(cnt[('played','pedal')]):>13s}   "
              f"{f(matched):>9s}")
    print("\n  WHY refused -- EDGE/MARGIN = the window no longer contains the feature (it MOVED);")
    print("  PROM = the window is right and there is no feature in it (presence/absence).  These")
    print("  are different findings and are counted separately (s151 vs s126/s133):")
    for name, _k, _w, _l in W.FEATURES:
        bits = []
        for cls in ("corner", "played"):
            for side in ("model", "pedal"):
                w = cens[name]["why"][f"{cls}_{side}"]
                if w:
                    bits.append(f"{cls[:4]}/{side[:3]} " +
                                "+".join(f"{k}:{v}" for k, v in sorted(w.items())))
        if bits:
            print(f"    {name:14s} " + "   ".join(bits))
    out["bv3"] = cens
    return cens


def _matched(rows, name, sel):
    """Every (capture, sweep) cell where BOTH sides read feature `name`, under filter `sel`."""
    cells = []
    for r in rows:
        if not sel(r):
            continue
        for sw in W.SWEEPS:
            m, p = r["model"][sw][name], r["pedal"][sw][name]
            if valid(m) and valid(p):
                cells.append((r, sw, m, p))
    return cells


def gate_bv4(rows, corner_cf, out):
    """CENTRE -- per feature, per GRUNT, matched membership, classified not quantified."""
    print("\n" + "=" * 96)
    print("BV4  CENTRE -- model vs pedal, MATCHED cells, computed classification")
    print("=" * 96)
    bar = RESOLUTION_FRAC * CENTRE_MULT
    print(f"  the locator resolves {100*RESOLUTION_FRAC:.2f} % (W's own GRID_STEP_FRAC/3); a centre")
    print(f"  error is called an OFFSET only past {100*bar:.2f} % ({CENTRE_MULT:.0f}x that).  ⛔ The")
    print( "  VERDICT is the finding; the percentages are context (s158/s159 -- the verdicts are")
    print( "  window-stable on both sides and the sizes move by up to 28.4 %).\n")
    res = {}
    for name, _k, _w, _l in W.FEATURES:
        res[name] = {}
        for cls, sel in (("corner", lambda r: is_corner(r, corner_cf)),
                         ("played", lambda r: not is_corner(r, corner_cf))):
            for g in ("cut", "flat", "boost"):
                cells = _matched(rows, name, lambda r, g=g, s=sel: s(r) and grunt_of(r) == g)
                if not cells:
                    print(f"  {name:13s} {cls:7s} grunt {g:5s}  REFUSED -- no matched cell")
                    res[name][f"{cls}_{g}"] = {"n": 0, "verdict": "REFUSED"}
                    continue

                def _v(cs):
                    if not cs:
                        return None, None, None
                    rat = [m["f0"] / p["f0"] for _r, _sw, m, p in cs]
                    sg, ab = med([x - 1.0 for x in rat]), med([abs(x - 1.0) for x in rat])
                    if ab <= bar:
                        return "TRACKS", ab, sg
                    return ("OFFSET model HIGH" if sg > 0 else "OFFSET model LOW"), ab, sg

                v, ab, sg = _v(cells)
                per_sw = {sw: _v([c for c in cells if c[1] == sw])[0] for sw in W.SWEEPS}
                stable = verdict_stable(per_sw)
                thin = len(cells) < MIN_N
                tag = ("  ⚠ THIN (n<%d) -- printed, NOT a verdict" % MIN_N) if thin else \
                      ("" if stable else "  ⚠⚠ NOT STABLE ACROSS STIMULUS: " +
                       " ".join(f"{s.replace('sweep_', ''):>7s}={short(per_sw[s])}"
                                for s in W.SWEEPS))
                print(f"  {name:13s} {cls:7s} grunt {g:5s}  n={len(cells):3d}  "
                      f"median |1-r| {100*ab:6.2f} %  signed {100*sg:+7.2f} %   "
                      f"{'THIN' if thin else v}{tag}")
                res[name][f"{cls}_{g}"] = {"n": len(cells), "abs_pct": 100 * ab,
                                           "signed_pct": 100 * sg,
                                           "verdict": "THIN" if thin else v,
                                           "pooled_verdict": v, "thin": thin,
                                           "stable": bool(stable), "per_sweep": per_sw}
    out["bv4"] = {"bar_pct": 100 * bar, "resolution_pct": 100 * RESOLUTION_FRAC, "features": res}
    return res


def gate_bv5(rows, corner_cf, out):
    """DEPTH -- BOTH estimators, per feature, per GRUNT, matched membership.

    ⛔ DEPTH only.  s192 AP3b measured `d(depth)/d(gain)` at 0.890 bleed-free and 0.299 at the mix,
    so a gain-unit statement is ~3.3x too tight at a played setting -- which is the whole population
    this gate exists to read.  Nothing here solves for a gain."""
    print("\n" + "=" * 96)
    print("BV5  DEPTH -- the comb's own contrast, POINT and AREA, both printed")
    print("=" * 96)
    print("  depth = the feature's level referred to its NEIGHBOURS in the comb (item 18/19's own")
    print("  `C1 = mid_peak - mid_notch`), positive = more contrast.  ⛔ NOT `locate()`'s `prom`,")
    print("  which GATE AU/AV/AW established is a DETECTOR that mixes depth with width.\n")
    res = {}
    for name, _k, _w, _l in W.FEATURES:
        res[name] = {}
        for cls, sel in (("corner", lambda r: is_corner(r, corner_cf)),
                         ("played", lambda r: not is_corner(r, corner_cf))):
            for g in ("cut", "flat", "boost"):
                cells = [(sw, m, p) for _r, sw, m, p in
                         _matched(rows, name, lambda r, g=g, s=sel: s(r) and grunt_of(r) == g)
                         if m["depth_point"] is not None and p["depth_point"] is not None]
                if not cells:
                    print(f"  {name:13s} {cls:7s} grunt {g:5s}  REFUSED -- no matched cell with shoulders")
                    res[name][f"{cls}_{g}"] = {"n": 0, "verdict": "REFUSED"}
                    continue

                def _v(cs):
                    if not cs:
                        return None, None, None
                    dp = med([m["depth_point"] - p["depth_point"] for _s, m, p in cs])
                    da = med([m["depth_area"] - p["depth_area"] for _s, m, p in cs])
                    if abs(da) <= DEPTH_TOL_DB:
                        return "MATCHES", dp, da
                    return ("model TOO DEEP/TALL" if da > 0 else "model TOO SHALLOW/FLAT"), dp, da

                # The verdict is taken on the AREA reading, and the POINT reading is printed beside
                # it always -- s152/s180/s186: the point depth is a LOWER BOUND wherever the null
                # bottom sits at/below the deconvolution residue, and at 4 of 6 bleed-free cells
                # s186 measured the two estimators disagreeing about the SIGN, i.e. recommending
                # OPPOSITE corrections.  Neither is allowed to stand alone.
                v, dp, da = _v(cells)
                agree = (dp > 0) == (da > 0)
                per_sw = {sw: _v([c for c in cells if c[0] == sw])[0] for sw in W.SWEEPS}
                stable = verdict_stable(per_sw)
                thin = len(cells) < MIN_N
                marks = ""
                if not agree:
                    marks += "  ⚠ ESTIMATORS DISAGREE ON SIGN"
                if thin:
                    marks += "  ⚠ THIN (n<%d) -- printed, NOT a verdict" % MIN_N
                elif not stable:
                    marks += "  ⚠⚠ NOT STABLE ACROSS STIMULUS: " + " ".join(
                        f"{s.replace('sweep_', ''):>7s}={short(per_sw[s])}" for s in W.SWEEPS)
                print(f"  {name:13s} {cls:7s} grunt {g:5s}  n={len(cells):3d}  "
                      f"POINT {dp:+7.2f} dB   AREA {da:+7.2f} dB   "
                      f"{'THIN' if thin else v}{marks}")
                res[name][f"{cls}_{g}"] = {"n": len(cells), "point_db": dp, "area_db": da,
                                           "sign_agree": bool(agree),
                                           "verdict": "THIN" if thin else v,
                                           "pooled_verdict": v, "thin": thin,
                                           "stable": bool(stable), "per_sweep": per_sw}
    out["bv5"] = {"tol_db": DEPTH_TOL_DB, "features": res}
    return res


def gate_bv6(centre, depth, out):
    """THE COMPARISON -- item 19's seven rows, re-read on the shipped build at PLAYED settings."""
    print("\n" + "=" * 96)
    print("BV6  ITEM 19's TABLE, RE-READ -- played settings, per GRUNT, both estimators")
    print("=" * 96)
    labels = {"bass_notch": "N1  bass null ~40-60 Hz", "bass_peak": "P1  bass peak ~160-210",
              "mid_notch": "N2  ~320 Hz null", "mid_peak": "P2  mid peak ~450",
              "bt_notch": "N3  ~800 Hz bridged-T", "treble_peak": "P3  treble peak ~2.9k",
              "treble_notch": "N4  treble null 6150-10708"}
    print(f"  {'#  feature':30s} {'centre (played)':34s} {'depth (played, AREA)':38s}")
    rowsout = {}
    n_stable = n_graded = 0
    for name, _k, _w, _l in W.FEATURES:
        cv, dv = [], []
        for g in ("cut", "flat", "boost"):
            c = centre[name].get(f"played_{g}", {})
            d = depth[name].get(f"played_{g}", {})
            cv.append(f"{g[0]}:{c.get('verdict', 'REFUSED').replace('OFFSET model ', '')[:9]}")
            if d.get("n", 0) == 0:
                dv.append(f"{g[0]}:REF")
            elif d.get("thin"):
                # ⚠ A THIN cell's NUMBER is still printed -- it is a real reading and hiding it
                # would hide membership -- but it is marked so it cannot be quoted as a result.
                dv.append(f"{g[0]}:{d['area_db']:+.2f}~")
            else:
                dv.append(f"{g[0]}:{d['area_db']:+.2f}")
            for blk in (c, d):
                if blk.get("n", 0) >= MIN_N:
                    n_graded += 1
                    n_stable += bool(blk.get("stable"))
        print(f"  {labels[name]:30s} {' '.join(cv):34s} {' '.join(dv):38s}")
        rowsout[name] = {"centre": {g: centre[name].get(f"played_{g}") for g in
                                    ("cut", "flat", "boost")},
                         "depth": {g: depth[name].get(f"played_{g}") for g in
                                   ("cut", "flat", "boost")}}
    print("\n  key: c/f/b = GRUNT cut/flat/boost.  centre TRACKS = within 3x the locator's own")
    print("       resolution.  depth = model - pedal in dB of comb contrast, AREA estimator;")
    print("       REF = refused (no matched cell), ~ = THIN (n<%d), not a verdict.  ⛔ Read BV4/BV5"
          % MIN_N)
    print("       for the POINT column and the corner class -- this table is the PLAYED summary.")
    frac = (100.0 * n_stable / n_graded) if n_graded else float("nan")
    print(f"\n  ⚠⚠ STIMULUS STABILITY, over both graded axes and every mix class: "
          f"{n_stable} of {n_graded} ({frac:.0f} %) non-thin cells give the SAME verdict at every")
    print( "     rung of the ladder they can be read on.  ⇒ s178's knife-edge is NOT confined to the")
    print( "     treble null: a large minority of this comb's verdicts DEPEND ON THE RUNG, so a")
    print( "     single-rung reading of any of them is not a property of the model.  Every unstable")
    print( "     cell is printed with its per-rung codes above.")
    out["bv6"] = {"rows": rowsout, "stability": {"stable": n_stable, "graded": n_graded,
                                                 "pct": frac}}


# =================================================================================================
def main():
    ap = argparse.ArgumentParser(description="GATE BV -- the final confirmation sweep")
    ap.add_argument("--report", default=DEFAULT_REPORT)
    ap.add_argument("--jobs", type=int, default=None)
    ap.add_argument("--out", default=OUT_JSON)
    args = ap.parse_args()

    out = {}
    fp_before = gate_bv0(args.report, out)
    files, ladder, base, extra = build_membership(args.report, out)
    print(f"\n  rendering/reading {len(files)} captures x {len(W.SWEEPS)} sweeps x 2 sides ...")
    rows = pmap(_cell, [(f, REN_DIR) for f in files], jobs=args.jobs)

    corner_cf = F.bleedfree_cf()
    print(f"  bleed-free corner clean fraction (DERIVED from the shipped end stop): {corner_cf:.5f}")

    gate_bv1(rows, base, extra, ladder, out)
    gate_bv2(rows, ladder, out)
    cens = gate_bv3(rows, corner_cf, out)
    centre = gate_bv4(rows, corner_cf, out)
    depth = gate_bv5(rows, corner_cf, out)
    gate_bv6(centre, depth, out)

    fp_after = dir_fingerprint(FORBIDDEN_DIR)
    out["bv0"]["forbidden_fp_after"] = fp_after
    if fp_after != fp_before:
        sys.exit(f"GATE BV: the READ-ONLY cache {FORBIDDEN_DIR} CHANGED during this run "
                 f"({fp_before} -> {fp_after}) -- an epoch five gates read has been destroyed")
    print(f"\n  ✅ READ-ONLY cache unchanged: {fp_before}")

    out["_cells"] = [{"file": r["file"], "cf": r["cf"], "grunt": grunt_of(r)} for r in rows]
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    json.dump(out, open(args.out, "w"), indent=1)
    print(f"  wrote {args.out}")
    _ = cens


if __name__ == "__main__":
    main()
