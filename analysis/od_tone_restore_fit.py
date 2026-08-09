#!/usr/bin/env python3.11
"""OdToneRestore — the SHAPE instrument for session 150's user-authorised notch/peak restore.

WHY THIS EXISTS, AND WHY IT IS NOT feature_locus_gate.py
--------------------------------------------------------
Session 150 tuned the restore stage against GATE W's `locate()` PROMINENCE, and stalled: the
prominence barely moved however much cut the biquad applied.  That gate's `mid_notch` window is a
FIXED [285, 358] Hz band and its prominence is `min(rise-to-left-edge, rise-to-right-edge)` — so
where the model's underlying curve DECLINES monotonically across the whole window, the argmin lands
on the right edge, the right-hand walk is empty, and the statistic reads ~0 for ANY notch depth.
`measurement-discipline.md` already carries this exact trap ("A PROMINENCE MEASURED AT A WINDOW EDGE
IS IDENTICALLY ZERO BY CONSTRUCTION", s126) — a prominence is a fine DETECTOR and a bad OBJECTIVE.

So this tool fits the thing the user actually asked for: the model's CURVE matching the pedal's
curve through 250-900 Hz.  It reports the shape-normalised difference `pedal - model` on GATE W's
own 1/48-oct log grid, using GATE W's own `smooth()`/`locate()` (imported, never transcribed), so
every number here is apples-to-apples with every prior GATE W / AD reading.  The prominences are
still printed — as a CHECK that follows from the shape, never as the thing being optimised.

THE OTHER HALF OF THE STALL: the fit set was DILUTED
----------------------------------------------------
The DRIVE ladder (`drive-*_base-od.wav`, `ref-od.wav`) sits at LEVEL = 0.5, BLEND = 1.0.  GATE K2
established that bleed vanishes only where BOTH are at max, and s113 measured LEVEL-noon/BLEND-max
output at ~44 % clean signal.  The restore stage is in the OD path, so at that mix roughly HALF of
whatever it does is diluted away before the output the analysis reads — a fit run there silently
prices in one particular LEVEL setting and would overshoot the moment the user turns LEVEL up.

`--set bleedfree` is therefore the FIT set (LEVEL = BLEND = max — the OD path measured directly,
drive rungs 0.0 / 0.5 / 1.0) and `--set listen` is the CHECK set (the full 5-rung ladder at the
user's own listening condition).  Fit on bleedfree; confirm on listen.  Do not fit on listen.

    python3.11 analysis/od_tone_restore_fit.py --set bleedfree
    python3.11 analysis/od_tone_restore_fit.py --set listen --band 200 1200
"""
import argparse
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import feature_locus_gate as W           # noqa: E402

REN_DIR = "build/s150_od_tone_restore"

# (capture, DRIVE knob).  Both sets are BLEND max; they differ only in LEVEL.
SETS = {
    # LEVEL max as well -> the OD path with no clean tap in the sum (GATE K2's bleed-free corner).
    "bleedfree": [
        ("drive-0700_level-1700_base-od.wav", 0.0),
        ("level-1700_base-od.wav", 0.5),
        ("drive-1700_level-1700_base-od.wav", 1.0),
    ],
    # LEVEL noon -> ~44 % clean bleed.  The user's listening condition; a CHECK, not a fit target.
    "listen": [
        ("drive-0700_base-od.wav", 0.0),
        ("drive-0930_base-od.wav", 0.25),
        ("ref-od.wav", 0.5),
        ("drive-1430_base-od.wav", 0.75),
        ("drive-1700_base-od.wav", 1.0),
    ],
    # The OTHER dilution axis.  LEVEL max, BLEND swept -> the clean tap is mixed in by BLEND alone,
    # so these check that an OD-path fit lands correctly at every mix and not just at one.  A fit
    # that is right in the OD path must track ALL of these with no further tuning; if it only fits
    # one BLEND position, the correction has absorbed a mix ratio and is a compensating error.
    "blend": [
        ("level-1700_base-od.wav", 0.5),          # BLEND max  = pure OD (the fit corner)
        ("level-1700_blend-1430_base-od.wav", 0.5),
        ("level-1700_blend-1200_base-od.wav", 0.5),
        ("level-1700_blend-0930_base-od.wav", 0.5),
    ],
    # ⚠⚠ THE GRUNT AXIS.  Every capture without a `grunt-` token is GRUNT = **CUT**
    # (`captures.py` defaults `gruntIdx=_GRUNT_IDX["cut"]`), so the whole fit above — and all of
    # session 150 — sits at ONE switch position.  That matters more here than anywhere else in the
    # project: `reference-sources.md` §3 records HARDWARE's 320 Hz null as deeper than ND's in all
    # six measured conditions, by **+1.6 dB at grunt cut rising to ~26 dB at grunt boost**, and §1
    # makes HARDWARE (not ND) the authority for this null's DEPTH.  So we have been fitting at the
    # position where the two references agree best, and the ND-matched answer is a LOWER BOUND on
    # what hardware wants — increasingly so as GRUNT opens up.
    # ⛔ Those are PNG reads: §3 says sign and rough size only, NEVER a fit target.  What these
    #   sets can do is measure whether ND's null deepens with GRUNT and whether the model tracks it.
    # The bleed-free DRIVE ladder at each of the other two GRUNT positions.  ⚠ `level-1700_grunt-*`
    # ARE bleed-free drive-noon captures (LEVEL = BLEND = max) — an earlier pass in s151 missed them
    # and nearly filed a capture request for data already on disk (`check-for-unread-data-first`).
    "grunt_flat": [
        ("drive-0700_level-1700_grunt-flat_base-od.wav", 0.0),
        ("level-1700_grunt-flat_base-od.wav", 0.5),
        ("drive-1700_level-1700_grunt-flat_base-od.wav", 1.0),
    ],
    "grunt_boost": [
        ("drive-0700_level-1700_grunt-boost_base-od.wav", 0.0),
        ("level-1700_grunt-boost_base-od.wav", 0.5),
        ("drive-1700_level-1700_grunt-boost_base-od.wav", 1.0),
    ],
    "grunt_hot": [
        ("drive-1700_level-1700_base-od.wav", 1.0),          # GRUNT cut
        ("drive-1700_level-1700_grunt-flat_base-od.wav", 1.0),
        ("drive-1700_level-1700_grunt-boost_base-od.wav", 1.0),
    ],
    "grunt_cold": [
        ("drive-0700_level-1700_base-od.wav", 0.0),          # GRUNT cut
        ("drive-0700_level-1700_grunt-flat_base-od.wav", 0.0),
        ("drive-0700_level-1700_grunt-boost_base-od.wav", 0.0),
    ],
    # BLEND swept at DRIVE max, where the notch deficit is largest and dilution bites hardest.
    "blend_hot": [
        ("drive-1700_level-1700_base-od.wav", 1.0),
        ("drive-1700_blend-1430_base-od.wav", 1.0),
        ("drive-1700_blend-1200_base-od.wav", 1.0),
        ("drive-1700_blend-0930_base-od.wav", 1.0),
        ("drive-1700_blend-0700_base-od.wav", 1.0),
    ],

    # ============================================================================================
    # THE MIXED TWINS — added session 186 (open item 19's task P3).  ⛔ EVERYTHING ABOVE THIS LINE
    # IS FROZEN: five other gates index these groups BY NAME (`null_depth_censor_gate.ROWS` and
    # through it GATE AQ and GATE AX; `model_prominence_gate`; `notch_shoulder_gate`), so a group
    # above must never change contents or every one of their stored numbers silently moves.
    # `check_sets()` pins them with a fingerprint, so this is asserted rather than intended.
    # ============================================================================================
    # WHY: measured at s186, the 8 groups above hold **17 of 29 rows at cf = 0.02418** and — far
    # sharper — **the GRUNT axis is 12 of 12 rows bleed-free**.  So this stage's GRUNT-ROWED tables
    # (`kNotchGainDb[3][5]`, `kNotchMixK[3][5]`, `kNotchQ[3][5]`) have only ever been graded at ONE
    # clean fraction, on the axis that has three rows to choose between.  The user's steer (s183 §9)
    # is that bleed-free is one setting and not the most used one; GATE BM (s184) then measured the
    # bleed-free corner to be unrepresentative on every one of the seven features.
    # ⚠ These are CHECK sets exactly as `listen` is — `--fit` still reads `bleedfree`, because the
    #   base row is anchored there by construction (s156) and re-pointing it is a RE-FIT, which P1
    #   measured as unnecessary (the applied cut moves 3.1x more at the corner, opposite sign).
    #
    # The DRIVE ladder at the LISTENING condition (LEVEL noon / BLEND max), per GRUNT position —
    # the direct mixed twins of `grunt_flat` / `grunt_boost`.  ⚠⚠ MEMBERSHIP IS ASYMMETRIC AND THAT
    # IS A CAPTURE FACT, NOT A CHOICE: `drive-1430_grunt-*` and `drive-1700_grunt-flat` do not
    # exist on disk, so flat reaches DRIVE 0.5 and boost reaches 1.0 while cut (`listen`) reaches
    # all five.  Named here so a pooled comparison across positions cannot quietly compare
    # different ladders (`aggregate-moved-check-membership-first`).
    "listen_flat": [
        ("drive-0700_grunt-flat_base-od.wav", 0.0),
        ("drive-0930_grunt-flat_base-od.wav", 0.25),
        ("grunt-flat_base-od.wav", 0.5),
    ],
    "listen_boost": [
        ("drive-0700_grunt-boost_base-od.wav", 0.0),
        ("drive-0930_grunt-boost_base-od.wav", 0.25),
        ("grunt-boost_base-od.wav", 0.5),
        ("drive-1700_grunt-boost_base-od.wav", 1.0),
    ],
    # The GRUNT axis read ACROSS positions at one drive — the mixed twins of `grunt_cold` (DRIVE 0)
    # and of the missing "grunt at drive noon" bleed-free group.  ⛔ There is NO mixed twin of
    # `grunt_hot` (DRIVE max across GRUNT): `drive-1700_grunt-flat_base-od.wav` is not on disk, and
    # capture access is ending (`reference-sources.md` §0), so that is a permanent gap rather than a
    # request.  Stated, not worked around.
    "grunt_mix": [
        ("ref-od.wav", 0.5),                        # GRUNT cut
        ("grunt-flat_base-od.wav", 0.5),
        ("grunt-boost_base-od.wav", 0.5),
    ],
    "grunt_cold_mix": [
        ("drive-0700_base-od.wav", 0.0),            # GRUNT cut
        ("drive-0700_grunt-flat_base-od.wav", 0.0),
        ("drive-0700_grunt-boost_base-od.wav", 0.0),
    ],
    # ⭐ THE LEVEL AXIS, WHICH NO GROUP ABOVE COVERS AT ALL.  `blend`/`blend_hot` sweep BLEND; the
    # LEVEL pot is held at max or noon everywhere else, so the one control the mix law is keyed
    # through has never been swept in this tool.  These are the 9 on-disk detents at BLEND max.
    # ⚠ Free corroboration of s185's own finding, visible in the cf column: the detents jump
    # 0.24382 (knob 0.875) straight to 0.02418 (knob 1.0), so the band P2's re-anchor disturbs
    # (cf in (0.02418, 0.20433)) contains NO capture — the gap is in the matrix, not in the law.
    "level_ladder": [
        ("level-0815_base-od.wav", 0.5),
        ("level-0930_base-od.wav", 0.5),
        ("level-1045_base-od.wav", 0.5),
        ("ref-od.wav", 0.5),                        # LEVEL noon (== `level-1200`, which has no file)
        ("level-1315_base-od.wav", 0.5),
        ("level-1430_base-od.wav", 0.5),
        ("level-1545_base-od.wav", 0.5),
        ("level-1700_base-od.wav", 0.5),            # the bleed-free corner, as the ladder's end
    ],
    # The LEVEL x BLEND interior — GATE BM's 3x3, every cell a real capture, none of them ever read
    # by this tool.  ⚠ These run cf 0.557 .. 0.978, i.e. mostly-clean, where the composite null
    # legitimately DISSOLVES and `notch_geometry` REFUSES.  A refusal is a reading of the physics,
    # not a failure (s151) — the point of including them is to establish WHERE the stage stops
    # being measurable at all, which no bleed-free set can say.
    "mixgrid": [
        ("level-0930_blend-1430_base-od.wav", 0.5),
        ("level-0930_blend-1200_base-od.wav", 0.5),
        ("level-0930_blend-0930_base-od.wav", 0.5),
        ("level-1200_blend-1430_base-od.wav", 0.5),
        ("level-1200_blend-1200_base-od.wav", 0.5),
        ("level-1200_blend-0930_base-od.wav", 0.5),
        ("level-1430_blend-1430_base-od.wav", 0.5),
        ("level-1430_blend-1200_base-od.wav", 0.5),
        ("level-1430_blend-0930_base-od.wav", 0.5),
    ],
}

# ⛔⛔ THE FROZEN GROUPS, PINNED BY CONTENT.  `null_depth_censor_gate.ROWS` names three of these and
# GATE AQ / GATE AX inherit it; `model_prominence_gate` and `notch_shoulder_gate` name "bleedfree"
# directly.  If any of them moved, five gates' stored numbers would shift with no diff anywhere near
# them — s146's `masterTaperBreak` failure with the blast radius spread across files.  So the
# guarantee "P3 was ADDITIVE" is asserted, not claimed.
FROZEN_SETS = ("bleedfree", "listen", "blend", "grunt_flat", "grunt_boost", "grunt_hot",
               "grunt_cold", "blend_hot")
FROZEN_ROWS = 29                          # measured s186 across the 8 frozen groups

# ---- what each group HOLDS and what it VARIES --------------------------------------------------
# Resolved from SETTINGS and asserted (s114: a substring/filename convention is a guess about a
# naming scheme, and naming schemes are not versioned).  `hold` is checked against every row's own
# parsed capture; `vary` is the axis the group exists to sweep and is NOT checked for constancy.
#   level/blend  -> the knob fraction as captured
#   grunt        -> PHYSICAL Clipper::Grunt position via grunt_pos_of() (0=cut, 1=flat, 2=boost)
#   drive        -> the tuple's own second element, checked against the capture (0 mismatches, s186)
SET_META = {
    "bleedfree":      {"hold": {"level": 1.0, "blend": 1.0, "grunt": 0}, "vary": "drive"},
    "listen":         {"hold": {"level": 0.5, "blend": 1.0, "grunt": 0}, "vary": "drive"},
    "blend":          {"hold": {"level": 1.0, "grunt": 0, "drive": 0.5}, "vary": "blend"},
    "grunt_flat":     {"hold": {"level": 1.0, "blend": 1.0, "grunt": 1}, "vary": "drive"},
    "grunt_boost":    {"hold": {"level": 1.0, "blend": 1.0, "grunt": 2}, "vary": "drive"},
    "grunt_hot":      {"hold": {"level": 1.0, "blend": 1.0, "drive": 1.0}, "vary": "grunt"},
    "grunt_cold":     {"hold": {"level": 1.0, "blend": 1.0, "drive": 0.0}, "vary": "grunt"},
    "blend_hot":      {"hold": {"grunt": 0, "drive": 1.0}, "vary": "blend"},
    "listen_flat":    {"hold": {"level": 0.5, "blend": 1.0, "grunt": 1}, "vary": "drive"},
    "listen_boost":   {"hold": {"level": 0.5, "blend": 1.0, "grunt": 2}, "vary": "drive"},
    "grunt_mix":      {"hold": {"level": 0.5, "blend": 1.0, "drive": 0.5}, "vary": "grunt"},
    "grunt_cold_mix": {"hold": {"level": 0.5, "blend": 1.0, "drive": 0.0}, "vary": "grunt"},
    "level_ladder":   {"hold": {"blend": 1.0, "grunt": 0, "drive": 0.5}, "vary": "level"},
    "mixgrid":        {"hold": {"grunt": 0, "drive": 0.5}, "vary": "level+blend"},
}

# A group is BLEED-FREE only where the clean coefficient vanishes, which is GATE K2's corner and
# nothing else.  ⚠⚠ Since s181's `blendEndStop` that corner is cf = 0.02418, NOT 0 — so the bar is
# a small band around the shipped end stop rather than an equality, and it is READ FROM THE HEADER
# rather than transcribed, so it cannot go stale the way GATE K2's own mirrors did at s182.
BLEEDFREE_CF_TOL = 1e-4


_BF_CF = [None]


def bleedfree_cf():
    """The clean fraction AT the bleed-free corner (LEVEL = BLEND = max), from the SHIPPED mix
    algebra — `coef_closed`, the same function `clean_frac_of` uses, so the two cannot disagree
    about what the corner is.

    ⚠⚠ NOT a transcription of 0.02418.  `level_law_gate.check_shipped_endstop()` is called first
    for its DIVERGENCE guard (s182: K2's two mirrors both went stale on s181's end stop while
    agreeing with each other to 5.6e-17, because both take the topology as INPUT), so if
    `FitParams::blendEndStop` ever moves this refuses instead of quietly returning the old corner."""
    if _BF_CF[0] is None:
        import level_law_gate as _LL
        _LL.check_shipped_endstop()               # refuses if FitParams.h has drifted
        od, cl = _LL.coef_closed(1.0, _LL.level_taper(1.0))
        _BF_CF[0] = (cl / (od + cl)) if (od + cl) > 0 else 1.0
    return _BF_CF[0]


def check_sets(verbose=False):
    """Assert every group's declared invariant against its rows' OWN parsed settings, and pin the
    frozen groups.  REFUSES rather than warning: a mis-declared group is not a degraded reading,
    it is a group measuring a different thing than its name says, and every statistic pooled over
    it inherits that silently."""
    e = bleedfree_cf()
    bad = []
    if tuple(k for k in FROZEN_SETS if k in SETS) != FROZEN_SETS:
        bad.append(f"a FROZEN group has been renamed or removed: {FROZEN_SETS}")
    nfroz = sum(len(SETS[k]) for k in FROZEN_SETS if k in SETS)
    if nfroz != FROZEN_ROWS:
        bad.append(f"the frozen groups hold {nfroz} rows, expected {FROZEN_ROWS} — five other "
                   f"gates index them by name; their stored numbers move if this changes")
    rows = []
    for name, meta in sorted(SET_META.items()):
        if name not in SETS:
            bad.append(f"SET_META names '{name}', which is not in SETS")
            continue
        for fname, drv in SETS[name]:
            p = C.parse_capture(fname)
            got = {"level": p["level"], "blend": p["blend"], "drive": p["drive"],
                   "grunt": grunt_pos_of(fname)}
            if abs(p["drive"] - drv) > 1e-9:
                bad.append(f"{name}/{fname}: declared DRIVE {drv} but the capture is {p['drive']}")
            for k, want in meta["hold"].items():
                if abs(got[k] - want) > 1e-9:
                    bad.append(f"{name}/{fname}: declares {k}={want} but the capture is {got[k]}")
            cf = clean_frac_of(fname)
            rows.append((name, fname, drv, cf, got["grunt"]))
    missing = sorted(set(SETS) - set(SET_META))
    if missing:
        bad.append(f"SETS has groups with no declared invariant: {missing}")
    if bad:
        sys.exit("od_tone_restore_fit: MEMBERSHIP REFUSED\n  " + "\n  ".join(bad))
    if verbose:
        print(f"  membership OK — {len(SET_META)} groups, {len(rows)} rows, "
              f"bleed-free corner cf = {e:.5f} (FitParams::blendEndStop)")
    return rows


def is_bleedfree(fname, e=None):
    e = bleedfree_cf() if e is None else e
    return abs(clean_frac_of(fname) - e) <= BLEEDFREE_CF_TOL

# Shape normalisation.  Both curves get their mean over this band removed before differencing, so
# what is compared is SHAPE and not level -- the same separation `comprehensive_report`'s per-row
# null gain makes, done explicitly here because this tool must NOT be blind to the level it removes.
NORM_LO, NORM_HI = 100.0, 8000.0

# The three features this session is about.  Imported from GATE W by NAME, never re-specified.
FEATS = ("mid_notch", "mid_peak", "bt_notch")


def curves(fname, sweep, ren_dir=REN_DIR, meta=False):
    """-> (grid, pedal_db, model_db), both shape-normalised on GATE W's own 1/48-oct grid.

    With `meta=True` a 4th element is returned carrying each side's deconvolution-residue floor
    EXPRESSED IN THE SAME NORMALISED dB as the curves, so a null bottom can be compared against
    it directly.  ⚠ That floor is DIAGNOSTIC ONLY and must never become an exclusion — it is
    signal-proportional regularisation residue, not a noise floor, and this project has deleted
    its own headline cells with it twice (GATE R's second floor guard, GATE W's first draft;
    `W.floor_db`'s docstring records both).  What it licenses is the opposite move: knowing WHICH
    depth readings are censored, so an estimator that does not depend on the bottom can be used
    there (GATE AP)."""
    orig, ref = W._load_orig()
    parsed = C.parse_capture(fname)
    out = os.path.join(ren_dir, fname.replace(".wav", "") + "_plugin.wav")
    W.render(out, C.render_args(parsed))       # binary-stamped: a stale build re-renders itself

    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)

    def one(al):
        f, m = A.transfer_h1(A.seg_of(al, sweep), ref)
        d = W.smooth(f, m)
        n = (W.GRID >= NORM_LO) & (W.GRID <= NORM_HI)
        off = float(np.mean(d[n]))
        return d - off, W.floor_db(f, m) - off

    (ped, pfl), (mod, mfl) = one(cap_al), one(ren_al)
    if meta:
        return W.GRID, ped, mod, {"ped_floor": pfl, "mod_floor": mfl}
    return W.GRID, ped, mod


def prom_table(d):
    return {n: W.locate(d, W.FEAT_BY_NAME[n][2], W.FEAT_BY_NAME[n][1]) for n in FEATS}


# ================================ THE FIT =======================================================
# The stage's own response, recomputed here from the SHIPPED constants so the fit solves for a
# DELTA on top of whatever is currently in the build, rather than assuming the stage is absent.
# Parsed out of the header (never transcribed) so it cannot drift from what the C++ runs.
HDR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "src", "dsp", "OdToneRestore.h")


def shipped_tables():
    """Parse the SHIPPED constants out of the header.

    ⚠⚠ The notch tables became GRUNT-ROWED (`[3][5]`) at s151 and this parser is versioned to
    match.  A parser that still matched `[5]` would find nothing and exit — which is the point:
    s146's `masterTaperBreak` lesson is that a name surviving a MEANING change silently rebuilds
    the wrong curve while producing entirely plausible numbers.  Refuse instead of guessing."""
    import re
    src = open(HDR).read()
    out = {}
    m = re.search(r"kX\[5\]\s*=\s*\{([^}]*)\}", src)
    if not m:
        sys.exit(f"od_tone_restore_fit: cannot parse kX out of {HDR}")
    out["kX"] = [float(v) for v in m.group(1).split(",")]
    # ⚠⚠ kNotchMixK IS REQUIRED, NOT OPTIONAL.  s156 made this stage MIX-KEYED, so kNotchGainDb
    # changed MEANING: it is now the cut at kMixCfRef, not the cut.  A parser that tolerated a
    # missing kNotchMixK would keep running and silently rebuild the pre-s156 two-table stage —
    # producing entirely plausible numbers that are wrong by up to 13 dB.  That is s146's
    # `masterTaperBreak` failure exactly, so this refuses instead (s151's own note above).
    for key in ("kNotchGainDb", "kNotchMixK", "kNotchQ"):
        m = re.search(rf"{key}\[3\]\[5\]\s*=\s*\{{(.*?)\n    \}};", src, re.S)
        if not m:
            sys.exit(f"od_tone_restore_fit: cannot parse {key}[3][5] out of {HDR} — if the table "
                     f"shape changed again, update THIS parser rather than letting it fall back")
        rows = re.findall(r"\{([^}]*)\}", m.group(1))
        if len(rows) != 3:
            sys.exit(f"od_tone_restore_fit: {key} has {len(rows)} GRUNT rows, expected 3")
        out[key] = [[float(v) for v in r.split(",") if v.strip()] for r in rows]
    for key in ("kMixCf", "kMixS"):
        m = re.search(rf"{key}\[kMixNodes\]\s*=\s*\{{(.*?)\}};", src, re.S)
        if not m:
            sys.exit(f"od_tone_restore_fit: cannot parse {key}[] out of {HDR}")
        out[key] = [float(v) for v in m.group(1).split(",") if v.strip()]
    if len(out["kMixCf"]) != len(out["kMixS"]):
        sys.exit("od_tone_restore_fit: kMixCf and kMixS have different lengths")
    m = re.search(r"kPeakGainDb\[5\]\s*=\s*\{([^}]*)\}", src)
    if not m:
        sys.exit(f"od_tone_restore_fit: cannot parse kPeakGainDb out of {HDR}")
    out["kPeakGainDb"] = [float(v) for v in m.group(1).split(",")]
    for key in ("kNotchFreq", "kPeakFreq", "kPeakQ", "kMixCfRef"):
        m = re.search(rf"{key}\s*=\s*([0-9.eE+-]+)\s*;", src)
        if not m:
            sys.exit(f"od_tone_restore_fit: cannot parse {key} out of {HDR}")
        out[key] = float(m.group(1))
    return out


# APVTS gruntIdx -> Clipper::Grunt position, mirroring PedalChain::gruntEnum().  Imported
# semantics, not a guess: APVTS order is {Boost, Cut, Flat}, the enum's is {Cut, Flat, Boost}.
_GRUNT_POS = {0: 2, 2: 1, 1: 0}


def grunt_pos_of(fname):
    return _GRUNT_POS.get(C.parse_capture(fname).get("gruntIdx", 1), 0)


def rbj_peak_db(f, fs, f0, q, gain_db):
    """RBJ peaking-EQ magnitude in dB.  Validated against the shipped C++ stage to 4e-6 dB
    (standalone impulse->DFT probe, session 151) — an INDEPENDENT implementation, not a port."""
    A = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * f0 / fs
    al = np.sin(w0) / (2.0 * max(q, 1e-6))
    c = np.cos(w0)
    b = np.array([1 + al * A, -2 * c, 1 - al * A])
    a = np.array([1 + al / A, -2 * c, 1 - al / A])
    b, a = b / a[0], a / a[0]
    z = np.exp(-1j * 2 * np.pi * np.asarray(f) / fs)
    return 20.0 * np.log10(np.abs((b[0] + b[1] * z + b[2] * z * z) / (1 + a[1] * z + a[2] * z * z)))


def lerp5(tab, x, kx):
    x = min(max(x, kx[0]), kx[-1])
    for i in range(4):
        if x <= kx[i + 1]:
            t = (x - kx[i]) / (kx[i + 1] - kx[i])
            return tab[i] + t * (tab[i + 1] - tab[i])
    return tab[4]


def mix_shape(cf, T):
    """S(cleanFrac) — MUST mirror OdToneRestore::mixShape().  Piecewise-linear over the header's
    own nodes, flat outside them.  Both sides read the same constants out of the same header, so
    the only thing that can diverge is this interpolation rule; `--selfcheck` asserts it against
    the shipped C++ via OfflineRender rather than trusting the transcription."""
    cfs, ss = T["kMixCf"], T["kMixS"]
    if cf <= cfs[0]:
        return ss[0]
    if cf >= cfs[-1]:
        return ss[-1]
    return float(np.interp(cf, cfs, ss))


def clean_frac_of(fname, taper=None):
    """The capture's clean fraction, from the SHIPPED mix algebra (GATE K's `coef_closed`,
    imported) fed the TAPERED level (s113).

    ⚠⚠ RE-POINTED s172.  This read `FitParams::levelTaperExp` and rebuilt `L = x ** p`.  That
    constant was RETIRED at s163 (the LEVEL law is now a 4-segment PWL) and DELETED rather than
    aliased, precisely so a missed consumer would fail loudly instead of silently rebuilding the
    old curve — which is what happened: this function has hard-exited since s163, taking every
    `--set`/`--fit` path that needs a mix with it, and nobody re-pointed it.  ⇒ call
    `level_law_gate.level_taper(x)`, the ONE implementation both languages are checked against.

    `taper` exists so a caller can evaluate a capture at a RETIRED epoch's curve (pass
    `level_law_gate.power_taper(2.25)`) — which is what a pre-s163 fit's numbers must be read at
    if they are to reproduce.  Default is always the shipped law."""
    import level_law_gate as _LL
    tf = _LL.level_taper if taper is None else taper
    p = C.parse_capture(fname)
    od, cl = _LL.coef_closed(p["blend"], tf(p["level"]))
    return (cl / (od + cl)) if (od + cl) > 0 else 1.0


def cut_db(T, grunt, drive, clean_frac=None):
    """THE EFFECTIVE CUT THE SHIPPED BUILD APPLIES at (grunt, drive, cleanFrac), in dB.

    ⛔⛔ SESSION 191 — EXTRACTED BECAUSE A CONSUMER HAD DRIFTED FROM IT AND NOTHING CAUGHT IT.
    Since s156 the stage is MIX-KEYED: `cut = kNotchGainDb + kNotchMixK * S(cleanFrac)`.
    `current_response` (below) computed that inline and correctly; GATE AP's AP3 compared its own
    solve against **`kNotchGainDb` ALONE** while subtracting `current_response`'s FULL mix-keyed
    curve — so it subtracted one stage and compared against a different one, and its load-bearing
    known answer AP3a duly read rms 6.48 dB against its own 2.49 bar (worst 9.86), i.e. RED, with
    the gate correctly refusing to let anything below it be quoted. The gap is exactly the term it
    omitted, and it is NOT small at the anchor: s185 pinned `S(e) = 0.951` there, so the mix term is
    near its full value precisely where the bleed-free membership reads.

    ⇒ ONE resolver, called by both, so the two cannot drift again — the `region_sel` /
    `level_law_gate._endstop` pattern, applied to this stage. `clean_frac=None` keeps
    `current_response`'s documented default (kMixCfRef, where S = 0) so every pre-s191 call is
    bit-identical; a caller reading a capture must pass `clean_frac_of(fname)`."""
    cf = T["kMixCfRef"] if clean_frac is None else clean_frac
    return (lerp5(T["kNotchGainDb"][grunt], drive, T["kX"])
            + lerp5(T["kNotchMixK"][grunt], drive, T["kX"]) * mix_shape(cf, T))


def current_response(f, drive, fs, T, grunt=0, clean_frac=None):
    """The stage's own response as the SHIPPED build computes it.

    ⚠⚠ s156: the cut is now base + K * S(cleanFrac), so `clean_frac` is a real argument.  It
    defaults to kMixCfRef (where S = 0), which reproduces the base table verbatim — the right
    default for a caller that genuinely has no mix, and WRONG for one that simply forgot to pass
    it.  Callers reading a capture must pass `clean_frac_of(fname)`."""
    cut = cut_db(T, grunt, drive, clean_frac)
    return (rbj_peak_db(f, fs, T["kNotchFreq"], lerp5(T["kNotchQ"][grunt], drive, T["kX"]), -cut)
            + rbj_peak_db(f, fs, T["kPeakFreq"], T["kPeakQ"],
                          lerp5(T["kPeakGainDb"], drive, T["kX"])))


# ⚠⚠ THE TREND IS FITTED JOINTLY AND DISCARDED, NOT EXTRAPOLATED FROM DISTANT SHOULDERS.
# First draft estimated a quadratic on shoulders at 195-275 and 1050-1500 Hz and subtracted it.
# That is wrong here and the tell was visible: the residual carried a smooth ~3 dB bowl centred
# ~500 Hz at two of three rungs, which is A3 — a BROADBAND OD-path deficit that lives right across
# the 275-1050 gap and therefore cannot be captured by a trend estimated outside it.  Fitting it
# there hands A3 to the notch/peak biquads, which is `one-knob-two-jobs-is-compensating` exactly.
# Fitted jointly, the quadratic is identifiable against two narrow biquads and is thrown away.
FIT_BAND = (250.0, 850.0)
F_REF = 400.0


def trend_basis(f):
    x = np.log(np.asarray(f) / F_REF)
    return np.vstack([np.ones_like(x), x, x * x]).T


# ================================ THE DEPTH READER ==============================================
# ⚠⚠ THE ARGMIN SEARCH AND THE SHOULDER SEARCH ARE DECOUPLED, AND THAT IS THE WHOLE POINT.
# GATE W's `locate()` does both inside ONE fixed window, which is why session 150's tuning stalled:
# [285, 358] Hz is narrower than the null's own shoulders, so the argmin sat on the right edge and
# the prominence read ~0 for any depth.  Widening that one window does not fix it either — at DRIVE
# max the model's curve falls monotonically from ~370 Hz all the way into the bridged-T notch, so a
# window wide enough to hold the right shoulder puts the GLOBAL minimum at ~550 Hz and the reader
# tracks the wrong feature (measured, s151: f0 550.8, depth 0.000, edge=1).
# ⇒ CORE bounds where the null itself demonstrably sits on both sides; SHOULDER bounds where its
#   flanks recover.  Neither is a fit and both are asserted below.
# ⚠⚠ THE DEFAULTS ARE THE **GRUNT CUT** WINDOWS AND DO NOT TRANSFER TO THE OTHER TWO POSITIONS.
# At GRUNT boost x DRIVE max the pedal's null migrates to ~242 Hz — outside CORE, and inside what
# GATE W calls `bass_peak` (110-285 Hz).  So a wider core is REQUIRED there, and the widening is
# not free: it crosses a named-feature boundary, so the reading must be checked for continuity
# against the same capture at lower drive before it is called "the same null that moved".
CORE = (285.0, 372.0)
SHOULDER = (210.0, 520.0)

# ---- THE AREA (POWER-INTEGRATED) DEPTH, GATE R's OWN REMEDY -------------------------------------
# ⚠⚠ WHY A SECOND DEPTH ESTIMATOR EXISTS AT ALL.  s151 fitted this stage's DEPTH against the
# pedal, and then found at the very end that most of the PEDAL's deep readings have their bottom AT
# OR BELOW the deconvolution residue (margins −27.7…+14.0 dB) — so those depths are LOWER BOUNDS,
# not measurements, and the two GRUNT rows fitted against them are provisional.
# ⛔ The move that is NOT available is dropping those cells: the residue is signal-PROPORTIONAL
# regularisation residue rather than a noise floor, and excluding on it deletes precisely the
# deep-notch cells a notch audit exists to measure (GATE R paid for this once, GATE W once).
# ⭐ GATE R's own resolution was to STOP DEPENDING ON THE FRAGILE QUANTITY (s110 R4): score a
# 1/6-octave POWER-INTEGRATED deficit, which is set by the notch's AREA rather than by the exact
# depth of its bottom, so it is barely moved by whether the last few dB down there are real.
# `null_locus_gate.band_db` is that function and it is IMPORTED, never re-derived — this wrapper
# only evaluates the same definition on the 1/48-oct grid the rest of this tool works on, and
# GATE AP asserts the two agree on identical data.
DEPTH_FRAC = 6           # 1/6 octave, GATE R's own width — at 323 Hz that is 285.6–365.1 Hz,
                         # i.e. almost exactly CORE, so the band matches this feature's own width.


def band_db_grid(g, d, centre, frac=DEPTH_FRAC):
    """POWER-average `d` (dB, on the 1/48-oct log grid) over a 1/`frac`-octave band about `centre`.

    Same inequality form as `null_locus_gate.band_db`, applied one level up the pipeline: that one
    integrates the raw Farina curve, this one integrates cells `W.smooth()` has ALREADY
    power-averaged.  Those compose only up to the per-cell bin weighting (a log cell high in the
    band holds more linear FFT bins than a low one), so the equivalence is ASSERTED by GATE AP
    rather than argued here."""
    lo, hi = centre * 2.0 ** (-0.5 / frac), centre * 2.0 ** (0.5 / frac)
    m = (g >= lo) & (g <= hi)
    if not m.any():
        return float(np.interp(centre, g, d))
    return float(10.0 * np.log10(np.mean(10.0 ** (np.asarray(d)[m] / 10.0))))


def notch_geometry(g, d, core=None, shoulder=None, depth="point"):
    """-> dict(f0, depth, q, lsh, rsh, depth_point, depth_area) for the 320 Hz null on ONE curve.

    `depth` selects which of the two goes in the `depth` key; BOTH are always returned, so no
    caller can quote one while believing it read the other.
      point — bottom and shoulders read as single grid cells.  What s150/s151 used.  Censored
              wherever the bottom sits at the deconvolution residue.
      area  — bottom and shoulders BOTH read as 1/6-octave power averages (GATE R's `notch()`
              requires the two to be read the same way, or they are not comparable).
    Either way the depth is referred to the SHALLOWER shoulder, the same min(left, right)
    conservatism GATE W's prominence uses.

    ⚠ `q` is ALWAYS the point-curve width at half the point depth.  A power-integrated depth has
    no width to speak of, and Q is a property of the FLANKS, which are not censored — mixing the
    two would produce a number neither estimator defines.

    ⛔⛔ `q` IS SEVERELY QUANTISED AND MUST NOT BE USED AS AN OBJECTIVE — USE `q_interp` (s153).
    The half-depth crossings are taken as whole GRID CELLS, so the width is an integer number of
    cells and `q` can only ever return f0/(k*df), df = f0*(2^(1/48)-1).  Measured on synthetic
    sections of known Q (GATE AQ's AQ1c): above Q~8 the attainable readings are {8.65, 11.54,
    17.31, ...} and NOTHING between, so true Q of 8, 10 and 11 all read 8.651 and true 18/20/24/30
    all read 17.310 — errors to -42 %, and the steps are 20-50 % wide, which is the SIZE of the
    defect this project is trying to measure with it.  ⇒ `OdToneRestore.h`'s "the Cut row stalls
    at 1.35-1.51 too broad" is ONE TO TWO STEPS of this reader, and its "EXACTLY on the pedal's
    11.54 at DRIVE max" is a quantisation coincidence (11.54 is a grid level).
    ⭐ `q_interp` interpolates each half-depth crossing linearly in log-f between the two cells
    that straddle it.  Same definition, same windows, same shoulders — only the crossing is no
    longer snapped to a cell.  It is strictly monotone in the true Q with no plateaus (AQ1c), which
    is what an objective needs; `q` is kept UNCHANGED so every pre-s153 number stays reproducible.
    ⚠ NEITHER is unbiased at low Q, and for the same reason AP1c documents for the depth: the
    SHOULDER window truncates a broad notch, so the shoulder-referred depth is less than the
    section's centre gain and the width read at half of it is too narrow.  Measured, `q_interp`
    runs +22 % at true Q=3 falling to +1 % by Q=11 and -5 % by Q=30.  That bias CANCELS in any
    pedal-vs-composite comparison read the same way, and it is why AQ1c gates on MONOTONICITY and
    on round-trip recovery rather than on absolute accuracy."""
    if depth not in ("point", "area"):
        raise ValueError(f"notch_geometry: depth must be 'point' or 'area', got {depth!r}")
    core = core or CORE
    shoulder = shoulder or SHOULDER
    c = (g >= core[0]) & (g <= core[1])
    ci = np.flatnonzero(c)
    i = int(ci[int(np.argmin(d[c]))])
    if i == ci[0] or i == ci[-1]:
        raise RuntimeError(f"notch_geometry: the minimum rests on a CORE bound ({g[i]:.1f} Hz) — "
                           f"the reader is tracking a bound, not a feature")
    s = (g >= shoulder[0]) & (g <= shoulder[1])
    si = np.flatnonzero(s)
    j = int(np.flatnonzero(si == i)[0])
    left, right = d[si[:j + 1]], d[si[j:]]
    li = int(si[int(np.argmax(left))])
    ri = int(si[j + int(np.argmax(right))])
    lsh, rsh = float(d[li]), float(d[ri])
    d_point = min(lsh, rsh) - float(d[i])
    d_area = (min(band_db_grid(g, d, g[li]), band_db_grid(g, d, g[ri]))
              - band_db_grid(g, d, g[i]))
    half = float(d[i]) + d_point / 2.0
    lo = hi = float(g[i])
    for k in range(j, -1, -1):
        if d[si[k]] >= half:
            lo = float(g[si[k]])
            break
    for k in range(j, len(si)):
        if d[si[k]] >= half:
            hi = float(g[si[k]])
            break

    # The same two crossings, interpolated in log-f between the straddling cells instead of being
    # snapped to one.  `lg` is log-frequency because the grid is logarithmic — interpolating in
    # linear Hz across a cell would introduce its own (small, but avoidable) bias.
    lgg = np.log(g)

    def _cross(order):
        prev = None
        for k in order:
            if d[si[k]] >= half:
                if prev is None:            # already at/above half at the bottom cell itself
                    return float(lgg[si[k]])
                a, b = float(d[si[prev]]), float(d[si[k]])
                t = 0.0 if b == a else (half - a) / (b - a)
                return float(lgg[si[prev]] + t * (lgg[si[k]] - lgg[si[prev]]))
            prev = k
        return None                          # never recovered inside the shoulder window

    xlo, xhi = _cross(range(j, -1, -1)), _cross(range(j, len(si)))
    q_interp = (float("nan") if xlo is None or xhi is None
                else float(g[i]) / max(np.exp(xhi) - np.exp(xlo), 1e-9))

    # ⭐ ADDITIVE (s154, GATE AR), same pattern as `q_interp` at s153: the two interpolated
    # half-depth crossings are returned SEPARATELY as well as through `q_interp`, because `q` and
    # `q_interp` are both WIDTHS and a width cannot express ASYMMETRY.  An RBJ peaking section is
    # symmetric in log-f by construction, so "is the pedal's null symmetric about its own bottom?"
    # is a question about a shape coordinate the (f0, Q, gain) family cannot span at any setting —
    # which is one of the two candidates s153 named for AQ4's residual.  Nothing existing reads
    # these keys, so every pre-s154 number, GATE AP's and GATE AQ's reports included, is unchanged
    # (asserted by re-running both and diffing).
    return {"f0": float(g[i]), "depth": d_area if depth == "area" else d_point,
            "depth_point": d_point, "depth_area": d_area,
            "q": float(g[i]) / max(hi - lo, 1e-9), "q_interp": q_interp, "lsh": lsh, "rsh": rsh,
            "bottom": float(d[i]), "lsh_f": float(g[li]), "rsh_f": float(g[ri]),
            "xlo_f": float("nan") if xlo is None else float(np.exp(xlo)),
            "xhi_f": float("nan") if xhi is None else float(np.exp(xhi))}


def do_matrix(args):
    """The CONFOUND matrix: null depth/Q on both sides across STIMULUS LEVEL x DRIVE.

    The stage tracks the DRIVE KNOB and nothing else, so it is static with respect to stimulus
    level by construction.  That is only defensible if the PEDAL's null is also ~static in stimulus
    level at fixed drive — which is a measurement nobody has taken, not an assumption to inherit.
    If the pedal's depth or Q moves materially across the four sweeps at one drive setting, a
    knob-keyed table CANNOT track it and this stage needs a different input (or an honest caveat)."""
    # ⚠ `--stage-off` was accepted here and SILENTLY IGNORED until s156 — the mode read the raw
    # rendered model whatever the flag said, so a run asking for "the requirement with our own
    # correction removed" quietly got "the requirement with it still in".  A flag that does
    # nothing is worse than one that errors, so it is honoured now.
    Tm = shipped_tables() if args.stage_off else None
    fsm = 48000.0 * W.OS_FACTOR
    print(f"\nCONFOUND MATRIX — stimulus level x drive, set '{args.which}'"
          + ("   [STAGE SUBTRACTED]" if args.stage_off else ""))
    print(f"  core {CORE} Hz, shoulders {SHOULDER} Hz;  depth/Q read on BOTH sides, one estimator")
    for fname, drv in SETS[args.which]:
        print("\n" + "=" * 92)
        print(f"DRIVE {drv:.2f}   {fname}")
        print("=" * 92)
        print(f"  {'sweep':<16} | {'ped f0':>7} {'ped dep':>8} {'ped Q':>6} | "
              f"{'mod f0':>7} {'mod dep':>8} {'mod Q':>6} | {'d dep':>7} {'Q rat':>6}")
        pw, mw = [], []
        for sw in W.SWEEPS:
            try:
                g, ped, mod = curves(fname, sw)
                if Tm is not None:
                    mod = mod - current_response(g, drv, fsm, Tm, grunt_pos_of(fname),
                                                 clean_frac_of(fname))
                p = notch_geometry(g, ped, depth=args.depth)
                m = notch_geometry(g, mod, depth=args.depth)
            except RuntimeError as e:
                print(f"  {sw:<16} | UNREADABLE: {e}")
                continue
            pw.append((p["depth"], p["q"]))
            mw.append((m["depth"], m["q"]))
            print(f"  {sw:<16} | {p['f0']:7.1f} {p['depth']:8.3f} {p['q']:6.2f} | "
                  f"{m['f0']:7.1f} {m['depth']:8.3f} {m['q']:6.2f} | "
                  f"{p['depth'] - m['depth']:+7.2f} {p['q'] / m['q']:6.2f}")
        if len(pw) > 1:
            pd = [a for a, _ in pw]
            pq = [b for _, b in pw]
            md = [a for a, _ in mw]
            print(f"  {'SPAN over sweeps':<16} | {'':7} {max(pd)-min(pd):8.3f} "
                  f"{max(pq)-min(pq):6.2f} | {'':7} {max(md)-min(md):8.3f}")
            print(f"    ^ if the PEDAL's span is large, a DRIVE-KNOB-keyed table cannot track it.")


def do_geom(args):
    # `--stage-off` subtracts the restore stage's OWN response analytically from the measured model
    # curve.  Exact, because the stage is linear and in series, so it needs no rebuild and no second
    # render -- and it is the only way to tell "the model never had a null here" apart from "our own
    # correction filled the null in", which look identical in the rendered curve.
    T = shipped_tables() if args.stage_off else None
    fs = 48000.0 * W.OS_FACTOR
    print(f"\nNULL GEOMETRY   sweep {args.sweep}   core {CORE} Hz, shoulders {SHOULDER} Hz"
          + f"   depth={args.depth}"
          + ("   [STAGE SUBTRACTED]" if args.stage_off else ""))
    print("=" * 88)
    print(f"  {'DRIVE':>5} | {'side':<5} {'f0':>7} {'depth':>7} {'Q':>6} | {'correction':>10} "
          f"{'Q ratio':>8} | capture")
    print("=" * 88)
    for fname, drv in SETS[args.which]:
        g, ped, mod = curves(fname, args.sweep)
        if T is not None:
            mod = mod - current_response(g, drv, fs, T, grunt_pos_of(fname), clean_frac_of(fname))
        try:
            p = notch_geometry(g, ped, depth=args.depth)
            m = notch_geometry(g, mod, depth=args.depth)
        except RuntimeError as e:
            # NOT an error to swallow silently: at heavy clean blend the null genuinely dissolves,
            # and refusing is the correct answer.  Reported per row so the row is never mistaken
            # for a measurement (`empty-gate-must-fail`).
            print(f"  {drv:5.2f} | NO READABLE NULL — {fname}\n        |   {e}")
            continue
        print(f"  {drv:5.2f} | {'pedal':<5} {p['f0']:7.1f} {p['depth']:7.3f} {p['q']:6.2f} |"
              f"{'':10} {'':8} | {fname}")
        print(f"  {'':5} | {'model':<5} {m['f0']:7.1f} {m['depth']:7.3f} {m['q']:6.2f} | "
              f"{p['depth'] - m['depth']:+10.2f} {p['q'] / m['q']:8.2f} |")
    print("\n  `correction` is the extra CUT still needed, in dB (negative = the model's null is "
          "already TOO deep).\n  A correction that changes sign across the ladder cannot come from "
          "any static element value.")


def fit_rung(g, ped, mod, drive, fs, T, notch_only=False, clean_frac=None, grunt=0):
    """Solve for the notch+peak the stage SHOULD have at this drive rung.

    target = (what the stage does now) + (what is still missing) -- so the answer is absolute
    stage parameters, not a correction to be applied by hand on top of the current table.

    ⚠⚠ SESSION 192 — `grunt` WAS HARDCODED 0 AND THAT MADE THIS TOOL CUT-ONLY BY CONSTRUCTION.
    `current_response` was called with a literal row index 0, so a caller fitting a `grunt_flat` /
    `grunt_boost` / `listen_boost` group added back GRUNT CUT's notch (Q and cut both) before
    solving, and the returned "cut the stage should apply" was a Cut-row answer wearing the other
    row's name.  Since s151 the tables are `[3][5]` and s186 added the mixed twins, so every GRUNT
    row is now a legitimate fit target.  Default 0 keeps every pre-s192 call bit-identical (asserted
    by re-running `--fit` and diffing), and `do_fit` now resolves the row PER CAPTURE via
    `grunt_pos_of` rather than from the group name — which is what the vary-grunt groups
    (`grunt_hot`, `grunt_cold`, `grunt_mix`) need, since they hold DRIVE and sweep GRUNT."""
    from scipy.optimize import least_squares

    lo, hi = FIT_BAND
    m = (g >= lo) & (g <= hi)
    f = g[m]
    # What the stage must deliver = what it already delivers + what is still missing.
    target = current_response(f, drive, fs, T, grunt, clean_frac) + (ped - mod)[m]
    B = trend_basis(f)

    def shape(p):
        fn, qn, gn, fp, qp, gp = p
        r = rbj_peak_db(f, fs, fn, qn, -gn)
        return r if notch_only else r + rbj_peak_db(f, fs, fp, qp, gp)

    def resid(p):
        r = target - shape(p)
        # project the smooth trend out of the residual: the biquads are never asked to
        # explain anything a quadratic in log-f can explain.  lstsq, so it is exact.
        co, *_ = np.linalg.lstsq(B, r, rcond=None)
        return r - B @ co

    lb = [295.0, 1.0, -6.0, 360.0, 0.5, -8.0]
    ub = [355.0, 20.0, 26.0, 620.0, 8.0, 10.0]
    best = None
    # Multi-start: an iterative fit seeded near its own answer proves nothing
    # (`known-answer-must-not-start-at-its-answer`), and this surface has local minima where the
    # notch and the peak swap roles.
    for f0 in (305.0, 324.0, 340.0):
        for q0 in (2.0, 6.0, 12.0):
            for gn0 in (0.0, 8.0):
                for fp0 in (420.0, 520.0):
                    try:
                        r = least_squares(resid, [f0, q0, gn0, fp0, 2.0, 0.0],
                                          bounds=(lb, ub), max_nfev=3000)
                    except Exception:
                        continue
                    if best is None or r.cost < best.cost:
                        best = r
    co, *_ = np.linalg.lstsq(B, target - shape(best.x), rcond=None)
    return best, f, target, co


def do_fit(args):
    T = shipped_tables()
    fs = 48000.0 * W.OS_FACTOR
    print(f"\nFIT  (stage runs at {fs:.0f} Hz = 48k x OS {W.OS_FACTOR})")
    print(f"  fitted over {FIT_BAND[0]:.0f}-{FIT_BAND[1]:.0f} Hz, with a quadratic-in-log-f trend "
          f"fitted JOINTLY and discarded (that trend is A3, not this stage's job)")
    # ⛔⛔ SESSION 192 — `--set` AND `--sweep` WERE BOTH DECLARED AND ONE WAS IGNORED HERE.
    # This loop read `SETS["bleedfree"]` as a literal while `--set` was already parsed and offered
    # (and `--geom`/`--matrix` honour it), so `--fit --set grunt_boost` silently fitted the
    # bleed-free CUT group and printed it under the caller's chosen name.  That is
    # `printed-is-not-scored` in its other direction: an option that exists, is documented in
    # `--help`, and does nothing on this path.  Now honoured, with the GRUNT row resolved per
    # capture so the vary-grunt groups work too.
    which = getattr(args, "which", "bleedfree")
    print(f"  set = {which}  (rows resolved per capture; sweep = {args.sweep})")
    g0 = grunt_pos_of(SETS[which][0][0])
    print(f"  shipped now (GRUNT row {g0}): fn={T['kNotchFreq']:.1f} Q={T['kNotchQ'][g0]} "
          f"gain={T['kNotchGainDb'][g0]}")
    print(f"               K={T['kNotchMixK'][g0]}")
    print(f"               fp={T['kPeakFreq']:.1f} Q={T['kPeakQ']} gain={T['kPeakGainDb']}")
    print("\n" + "=" * 100)
    print(f"  {'DRIVE':>6} {'g':>2} | {'notch f0':>9} {'notch Q':>8} {'notch dB':>9} | "
          f"{'peak f0':>8} {'peak Q':>7} {'peak dB':>8} | {'rms':>6} | {'shipped cut':>11} "
          f"| discarded trend @400Hz")
    print("=" * 100)
    res = {}
    for fname, drv in SETS[which]:
        gpos = grunt_pos_of(fname)
        cf = clean_frac_of(fname)
        g, ped, mod = curves(fname, args.sweep)
        best, f, target, co = fit_rung(g, ped, mod, drv, fs, T, clean_frac=cf, grunt=gpos)
        fn, qn, gn, fp, qp, gp = best.x
        rms = float(np.sqrt(np.mean(best.fun ** 2)))
        res[(gpos, drv)] = best.x
        print(f"  {drv:6.2f} {gpos:2d} | {fn:9.1f} {qn:8.2f} {gn:9.2f} | {fp:8.1f} {qp:7.2f} "
              f"{gp:8.2f} | {rms:6.3f} | {cut_db(T, gpos, drv, cf):11.2f} "
              f"| {co[0]:+6.2f} dB, slope {co[1]:+5.2f}, curv {co[2]:+5.2f}")
    print("\n  notch dB is the CUT to apply (positive number = cut that many dB).")
    print("  ⚠ these are per-rung free fits — read them for the TREND, then impose one f0/one Q law")
    print("    rather than shipping three unrelated triples.")
    return res


def do_sets(_args):
    """The MEMBERSHIP AUDIT — what each group actually holds, in clean fraction.

    This exists because the imbalance it prints was invisible for 35 sessions: every group is
    named for the axis it sweeps, and NOTHING in the tool said what mix those sweeps sit at.  A
    group called `grunt_flat` reads as "the GRUNT flat condition", not as "the GRUNT flat condition
    at the one clean fraction the pot cannot reach in normal use"."""
    rows = check_sets()
    e = bleedfree_cf()
    print(f"\nSET MEMBERSHIP AUDIT   bleed-free corner cf = {e:.5f} "
          f"(LEVEL = BLEND = max, via FitParams::blendEndStop)")
    print("=" * 100)
    print(f"  {'group':<16} {'n':>3} {'varies':<12} {'cf min':>8} {'cf max':>8} {'GRUNT':<14} "
          f"{'DRIVE rungs':<22} kind")
    print("=" * 100)
    nbf_rows = nbf_groups = 0
    for name in sorted(SET_META):
        rs = [r for r in rows if r[0] == name]
        cfs = [r[3] for r in rs]
        drv = sorted({r[2] for r in rs})
        gr = sorted({r[4] for r in rs})
        gnames = "/".join(("cut", "flat", "boost")[g] for g in gr)
        nbf = sum(1 for c in cfs if abs(c - e) <= BLEEDFREE_CF_TOL)
        nbf_rows += nbf
        kind = "BLEED-FREE" if nbf == len(rs) else ("mixed" if nbf == 0 else f"mixed ({nbf} bf)")
        if nbf == len(rs):
            nbf_groups += 1
        print(f"  {name:<16} {len(rs):3d} {SET_META[name]['vary']:<12} {min(cfs):8.5f} "
              f"{max(cfs):8.5f} {gnames:<14} {','.join(f'{d:g}' for d in drv):<22} {kind}")
    tot = len(rows)
    print("=" * 100)
    print(f"  TOTAL {tot} rows in {len(SET_META)} groups;  bleed-free: {nbf_rows} rows "
          f"({100.0*nbf_rows/tot:.0f} %), {nbf_groups} whole groups")
    # The axis-level statement, which is the one that matters: a 3-row table graded at one cf.
    gr_rows = [r for r in rows if SET_META[r[0]]["vary"] == "grunt"
               or r[0] in ("bleedfree", "grunt_flat", "grunt_boost", "listen",
                           "listen_flat", "listen_boost")]
    gbf = sum(1 for r in gr_rows if abs(r[3] - e) <= BLEEDFREE_CF_TOL)
    print(f"  GRUNT-bearing rows: {gbf} of {len(gr_rows)} bleed-free "
          f"({100.0*gbf/max(len(gr_rows),1):.0f} %)")
    print("\n  ⚠ `kind` is computed from each row's own cf, never from its filename — every capture "
          "without a\n    `grunt-` token is GRUNT = CUT and every one without `level-` is LEVEL "
          "noon, and both of those\n    have cost this project a whole session (s151, s172 §6).")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sets", action="store_true", help="membership audit: what mix each group is at")
    ap.add_argument("--fit", action="store_true", help="solve for the stage's parameters per rung")
    ap.add_argument("--geom", action="store_true", help="read the 320 Hz null's depth/Q both sides")
    ap.add_argument("--matrix", action="store_true", help="depth/Q across stimulus level x drive")
    ap.add_argument("--stage-off", action="store_true",
                    help="subtract the restore stage's own response (exact; no rebuild needed)")
    ap.add_argument("--set", dest="which", default="bleedfree", choices=sorted(SETS))
    ap.add_argument("--depth", default="point", choices=("point", "area"),
                    help="point = bottom/shoulder grid cells (s150/s151, censored by the "
                         "deconvolution residue at deep nulls); area = 1/6-oct POWER-INTEGRATED "
                         "on both, GATE R's own remedy (s110 R4).  See GATE AP.")
    ap.add_argument("--sweep", default="sweep_drv_-12")
    ap.add_argument("--band", nargs=2, type=float, default=[240.0, 1000.0])
    ap.add_argument("--step", type=int, default=2, help="print every Nth grid cell")
    args = ap.parse_args()

    # Membership is checked on EVERY path, not only under `--sets`: a mis-declared group poisons
    # `--geom` and `--matrix` exactly as badly, and a guard that only runs when asked is a guard
    # that runs when someone already suspects the answer.
    check_sets()

    if args.sets:
        do_sets(args)
        return
    if args.fit:
        do_fit(args)
        return
    if args.geom:
        do_geom(args)
        return
    if args.matrix:
        do_matrix(args)
        return

    rows = SETS[args.which]
    lo, hi = args.band
    print(f"\nSET {args.which}   sweep {args.sweep}   shape-normalised over "
          f"{NORM_LO:.0f}-{NORM_HI:.0f} Hz   (grid 1/48 oct)")
    if args.which == "listen":
        print("  ⚠ LEVEL noon => ~44 % clean bleed dilutes anything the OD-path stage does. "
              "CHECK set, not a fit target.")

    store = {}
    for fname, drv in rows:
        g, ped, mod = curves(fname, args.sweep)
        store[(drv, fname)] = (g, ped, mod)

        m = (g >= lo) & (g <= hi)
        diff = ped - mod
        print("\n" + "=" * 78)
        print(f"DRIVE {drv:.2f}   {fname}")
        print("=" * 78)
        print(f"  {'f Hz':>8} {'pedal':>9} {'model':>9} {'P-M':>8}")
        idx = np.flatnonzero(m)[:: max(1, args.step)]
        for i in idx:
            print(f"  {g[i]:8.1f} {ped[i]:9.3f} {mod[i]:9.3f} {diff[i]:8.3f}")

        pp, mp = prom_table(ped), prom_table(mod)
        print(f"  {'feature':<12} {'pedal f0':>9} {'prom':>7} | {'model f0':>9} {'prom':>7} "
              f"| {'deficit':>8}  edge(P/M)")
        for n in FEATS:
            print(f"  {n:<12} {pp[n]['f0']:9.1f} {pp[n]['prom']:7.3f} | "
                  f"{mp[n]['f0']:9.1f} {mp[n]['prom']:7.3f} | "
                  f"{pp[n]['prom'] - mp[n]['prom']:8.3f}  "
                  f"{int(pp[n]['edge'])}/{int(mp[n]['edge'])}")

    # ---- the summary the tuning actually needs: worst shape error inside the target band --------
    print("\n" + "=" * 78)
    print(f"SHAPE ERROR (pedal - model) over {lo:.0f}-{hi:.0f} Hz")
    print("=" * 78)
    print(f"  {'DRIVE':>6} {'rms':>8} {'mean':>8} {'min':>8} {'max':>8}   "
          f"{'argmax f':>9} {'argmin f':>9}")
    for (drv, fn_), (g, ped, mod) in sorted(store.items()):
        m = (g >= lo) & (g <= hi)
        d = (ped - mod)[m]
        gg = g[m]
        print(f"  {drv:6.2f} {np.sqrt(np.mean(d**2)):8.3f} {np.mean(d):8.3f} "
              f"{np.min(d):8.3f} {np.max(d):8.3f}   "
              f"{gg[int(np.argmax(d))]:9.1f} {gg[int(np.argmin(d))]:9.1f}   {fn_}")
    print("\n  A NEGATIVE P-M means the MODEL is HOT there (needs cut); positive means it is quiet "
          "(needs boost).")


if __name__ == "__main__":
    main()
