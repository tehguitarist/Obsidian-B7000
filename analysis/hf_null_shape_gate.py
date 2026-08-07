#!/usr/bin/env python3.11
"""GATE BH — the HF cancellation null's DEPTH-vs-STIMULUS ORDERING.  Session 178, open item 17.

WHY AN ORDERING GATE, AND NOT A DEPTH ONE
-----------------------------------------
`reference-sources.md` §1 gives **neither** reference authority over this null:

    | 5-6 kHz null | **Neither — unresolved** | absent from the clean sweep, so drive-dependent;
                                                the driven charts disagree between conditions |

and §3's own row for it reads *"Inconsistent — ND ~11 dB deeper at Attack cut, HW far deeper at
Grunt cut"*, with no number attached to "far deeper".  s170 established the source images are no
longer on disk, so that cannot be refined.  ⇒ **there is no target for this null's DEPTH, and any
gate that scores distance-to-ND on it is scoring a quantity no reference governs.**

What IS gradeable is the SHAPE of its dose-response.  The null is an OD-vs-clean CANCELLATION, so
its depth peaks at whichever stimulus makes the two branches equal in magnitude at that frequency.
That makes "which rung is deepest" a statement about the model's gain STRUCTURE, not about a depth
either reference has authority over — and it is gradeable as an ORDERING, with no threshold, in
exactly the way GATE AD grades the hardware trend (`reference-sources.md` §5 rule 3).

Measured, ND's depth falls MONOTONICALLY with stimulus, and so does the pre-s172 model.  The
shipped build does not: it is 11 dB too SHALLOW at the quiet rung and 20 dB too DEEP at the user's
playing rung (`drv_-12`), because its depth peak has slid up the stimulus ladder.

⛔⛔ **DEPTH IS A KNIFE-EDGE HERE AND MUST NEVER BE A FIT TARGET.**  On `ref-od` the shipped depth
runs 2.58 / 24.78 / 6.83 dB across a 12 dB stimulus span and the pre-s172 arm runs 34.11 / 7.11 /
2.96 over the SAME three renders.  A near-perfect cancellation is deep and narrow; a slightly
detuned one is neither.  A session that reads one rung will conclude the model is 20 dB too deep,
or 11 dB too shallow, depending only on which rung it read — this gate exists partly to stop that
(`an-endpoint-pair-is-not-a-ladder`, s129; the first draft of session 178 committed it).

THE MECHANISM, WHICH IS COMPUTABLE AND PREDICTS THE DEFECT
---------------------------------------------------------
Raising the OD branch slides the |OD| = |clean| crossing UP the stimulus ladder, because the OD
branch compresses with stimulus and the clean tap does not.  The OD-branch gain AT THE NULL is
therefore the lever, and it is arithmetic on the shipped constants:

    s172:  +6.0 (flat)  - 6.0 (high shelf, corner 2800)          =  0.0 dB at ~5.5 kHz
    s173:  +6.0 (flat)  - 3.0 (high shelf, corner 1600)  + 3.3   = +6.3 dB at ~5.5 kHz
                             ^^^ HALVED                    ^^^ NEW peak, centred 5600 Hz

⇒ s172 left the null's own frequency at unity and preserved the ordering; s173 added ~6.3 dB there
and inverted it.  BH3 asserts that arithmetic against the RENDER rather than trusting it.

⚠⚠ **THIS IS NOT A LICENCE TO REVERT s173.**  s173's shelf change fixed a USER-REPORTED regression
— the notch centre had walked ~5.3 -> ~4 kHz, monotone in 18 of 18 driven cells (GATE BF) — and the
median model/pedal centre ratio went 0.759 -> 0.837 -> 0.926 with the HF term.  Restoring s172's
shelf restores the ORDERING and gives that centre gain back.  BH4 therefore grades BOTH axes and
BH5 refuses any candidate that buys one with the other.  ⇒ the deliverable is a FRONTIER, not a
winner.

Run:
    /opt/homebrew/bin/python3.11 analysis/hf_null_shape_gate.py
    /opt/homebrew/bin/python3.11 analysis/hf_null_shape_gate.py --json analysis/reports/s178_hf_null_shape.json
"""
import argparse
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import feature_locus_gate as W           # noqa: E402
import od_tone_restore_fit as F          # noqa: E402

REN_DIR = "build/s178_hf_null_shape"     # PRIVATE — never GATE W's read-only s122 cache

# ---- membership.  NAMED, asserted, and split by the two axes that matter -----------------------
# ⚠⚠ Every capture without a `grunt-` token is GRUNT = CUT (`captures.py` defaults gruntIdx), the
# trap that cost s151 a whole fit.  The GRUNT axis is therefore spelled out explicitly.
CONDITIONS = [
    # (label,                capture,                                  grunt,  mix)
    ("listen drv0.5 cut",    "ref-od.wav",                             "cut",   "listen"),
    ("listen drv0.5 flat",   "grunt-flat_base-od.wav",                 "flat",  "listen"),
    ("listen drv0.5 boost",  "grunt-boost_base-od.wav",                "boost", "listen"),
    ("listen drv1.0 cut",    "drive-1700_base-od.wav",                 "cut",   "listen"),
    ("listen drv1.0 boost",  "drive-1700_grunt-boost_base-od.wav",     "boost", "listen"),
    ("listen drv0.0 cut",    "drive-0700_base-od.wav",                 "cut",   "listen"),
    ("blend 1430 cut",       "level-1700_blend-1430_base-od.wav",      "cut",   "blend"),
    ("blend 1200 cut",       "level-1700_blend-1200_base-od.wav",      "cut",   "blend"),
    ("blend 0930 cut",       "level-1700_blend-0930_base-od.wav",      "cut",   "blend"),
    ("bleedfree drv0.5 cut", "level-1700_base-od.wav",                 "cut",   "bleedfree"),
]

# ⚠ `sweep_clean` is EXCLUDED and the exclusion is a MEASUREMENT, not a convenience: the model has
# no interior extremum in the treble window at clean stimulus (GATE AE's finding, reproduced by
# BH0c every run), so a rung where one side cannot be read cannot enter an ordering.
RUNGS = ("sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
PLAYING_RUNG = "sweep_drv_-12"           # the user's stated playing level

# ---- the TWO nulls, and they are ONE mechanism at the two band edges ---------------------------
# ⚠⚠ THE USER'S "bass notch" IS THE ~40-60 Hz ONE, NOT THE 320 Hz NULL.  Those are different
# features with OPPOSITE hardware stories and conflating them inverts the recommendation:
#   * mid_notch (~320 Hz): §1 makes HARDWARE the authority and §3 records it DEEPER than ND
#     (+1.6 dB at GRUNT cut rising to ~26 at boost) ⇒ our overshoot there is a §5 rule 2 PASS.
#     NOT graded here — it is measured and closed in session 178's log.
#   * bass_notch (~40-60 Hz): §3's LF row records HW at 18 Hz vs ND at 35 Hz (grunt boost) and,
#     at attack boost, the SAME frequency with **ND ~10 dB DEEPER** ⇒ at this null hardware wants
#     SHALLOWER than ND, so a model deeper than ND is moving AWAY from hardware.  Both references
#     agree on the direction, which is the strongest case in the whole item.
#   * treble_notch (measured 6150-10708 Hz): §1 gives NEITHER reference authority ⇒ ordering only.
# Windows imported from GATE W by NAME (s133: quote the measured band, never the "4.5-6 kHz"
# label — only 35 of 192 readings fall inside it).
FEATURES = {
    "bass_notch":   (W.FEAT_BY_NAME["bass_notch"][2],   (22.0, 300.0)),
    "treble_notch": (W.FEAT_BY_NAME["treble_notch"][2], (2800.0, 16000.0)),
}
# The feature whose DEPTH is gradeable (both references agree on the direction).  The treble one
# is ordering-only and its depth is printed, never scored.
DEPTH_GRADED = "bass_notch"
ORDER_GRADED = "treble_notch"

# ---- the arms ----------------------------------------------------------------------------------
HF_OFF = ("--fit", "odMakeupHfAtOdDb=0", "--fit", "odMakeupHfPeakDb=0", "--fit", "odMakeupHfAtCleanDb=0")
MK_OFF = ("--fit", "odMakeupDb=0", "--fit", "odMakeupLowCutDb=0", "--fit", "odMakeupHighCutDb=0")
S172 = ("--fit", "odMakeupHighHz=2800", "--fit", "odMakeupHighCutDb=6.0") + HF_OFF

LOWCUT = {d: ("--fit", f"odMakeupLowCutDb={d}") for d in (0.0, 6.0)}

ARMS = {
    "ship (s173)":  (),
    "s173 no-HF":   HF_OFF,
    "s172 shelf":   S172,
    "pre-s172":     HF_OFF + MK_OFF,
    "lowCut 0":     LOWCUT[0.0],       # the LF lever, both ends — bass_notch's dose-response
    "lowCut 6":     LOWCUT[6.0],
}
BASELINE_ARM = "ship (s173)"
# The LF dose-response, as (odMakeupLowCutDb, arm).  `None` = the shipped value, read from
# FitParams so this cannot drift from what ships.
LOWCUT_LADDER = [(0.0, LOWCUT[0.0]), (None, ()), (6.0, LOWCUT[6.0]), (float("inf"), HF_OFF + MK_OFF)]

CLEAN_CONTROL = "blend-0700_base-od.wav"   # BLEND = 0 -> the OD branch is out of circuit entirely


def die(tag, msg):
    print(f"\n⛔ {tag}: {msg}")
    sys.exit(1)


# ================================================================================================
def _tag(arm):
    return "" if not arm else "__" + "_".join(a.replace("=", "") for a in arm if a != "--fit")


def render_of(fname, arm):
    parsed = C.parse_capture(fname)
    out = os.path.join(REN_DIR, fname.replace(".wav", "") + _tag(arm) + "_plugin.wav")
    W.render(out, C.render_args(parsed, extra_args=list(arm)))
    return out


_CURVES = {}


def curves(fname, sweep, arm):
    """-> (grid, pedal_db, model_db), shape-normalised on GATE W's own 1/48-oct grid.

    Same normalisation as `od_tone_restore_fit.curves` (its NORM_LO/NORM_HI are IMPORTED, not
    restated) so every number here is apples-to-apples with the OdToneRestore instruments."""
    key = (fname, sweep, arm)
    if key in _CURVES:
        return _CURVES[key]
    out = render_of(fname, arm)
    orig, ref = W._load_orig()
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)

    def one(al):
        f, m = A.transfer_h1(A.seg_of(al, sweep), ref)
        d = W.smooth(f, m)
        n = (W.GRID >= F.NORM_LO) & (W.GRID <= F.NORM_HI)
        return d - float(np.mean(d[n]))

    _CURVES[key] = (W.GRID, one(cap_al), one(ren_al))
    return _CURVES[key]


def geom(g, d, feat=ORDER_GRADED):
    """The E6 estimator (`od_tone_restore_fit.notch_geometry`), IMPORTED — never re-derived.

    ⛔ NOT GATE W's `locate()` prominence: AW6 (s159) proved E1 <= E6 identically and that the
    gap between them is a WIDTH statistic, so an E1 prominence mixes depth with width and cannot
    be read as a depth.  Returns None where the estimator refuses (minimum on a CORE bound)."""
    core, sh = FEATURES[feat]
    try:
        return F.notch_geometry(g, d, core=core, shoulder=sh)
    except Exception:
        return None


def mono_falling(v):
    return None if any(x is None for x in v) else all(v[i] > v[i + 1] for i in range(len(v) - 1))


def matched_cells(feat, unit):
    """The cells readable by ND **and every arm** — the only population any arm may be compared on.

    ⚠⚠ THIS IS NOT BOOKKEEPING.  A first draft of this gate pooled each arm over whatever it could
    read (n = 17 / 17 / 17 / 19 / 15 / 18) and printed the means side by side, which is
    `aggregate-moved-check-membership-first` in its purest form — the arm with the fewest readable
    cells looked best because a cancellation that is too shallow to READ is silently dropped, and
    "too shallow to read" is exactly the outcome being scored.  Twelve prior occurrences in this
    project; s159's is the closest (an admission BAR moving the population inside one epoch).

    `unit` is "condition" (all RUNGS must resolve — the ordering statistic's unit) or "cell"
    (one (condition, rung) — the depth statistic's unit).  Returns (kept, dropped)."""
    kept, dropped = [], []
    for label, fname, _, _ in CONDITIONS:
        rungs = RUNGS if unit == "condition" else RUNGS
        for sw in ([None] if unit == "condition" else rungs):
            probe = rungs if unit == "condition" else [sw]
            ok = True
            for side_arm in [()] + [a for a in ARMS.values()]:
                for r in probe:
                    g, ped, mod = curves(fname, r, side_arm)
                    if geom(g, ped, feat) is None or geom(g, mod, feat) is None:
                        ok = False
                        break
                if not ok:
                    break
            (kept if ok else dropped).append(label if unit == "condition" else (label, sw))
    return kept, dropped


def binom_tail(k, n, p):
    """P(X >= k) for X ~ Binom(n, p).  Exact — no normal approximation, no invented threshold."""
    return float(sum(math.comb(n, i) * p ** i * (1 - p) ** (n - i) for i in range(k, n + 1)))


# ---- the OD-branch transfer, implemented INDEPENDENTLY of the C++ and then asserted against it --
def rbj_shelf_db(f, fs, f0, gain_db, S, high):
    Amp = 10.0 ** (gain_db / 40.0)
    w0 = 2.0 * np.pi * f0 / fs
    alpha = np.sin(w0) / 2.0 * np.sqrt((Amp + 1.0 / Amp) * (1.0 / S - 1.0) + 2.0)
    cw, sq = np.cos(w0), 2.0 * np.sqrt(Amp) * alpha
    if high:
        b0 = Amp * ((Amp + 1) + (Amp - 1) * cw + sq)
        b1 = -2 * Amp * ((Amp - 1) + (Amp + 1) * cw)
        b2 = Amp * ((Amp + 1) + (Amp - 1) * cw - sq)
        a0 = (Amp + 1) - (Amp - 1) * cw + sq
        a1 = 2 * ((Amp - 1) - (Amp + 1) * cw)
        a2 = (Amp + 1) - (Amp - 1) * cw - sq
    else:
        b0 = Amp * ((Amp + 1) - (Amp - 1) * cw + sq)
        b1 = 2 * Amp * ((Amp - 1) - (Amp + 1) * cw)
        b2 = Amp * ((Amp + 1) - (Amp - 1) * cw - sq)
        a0 = (Amp + 1) + (Amp - 1) * cw + sq
        a1 = -2 * ((Amp - 1) + (Amp + 1) * cw)
        a2 = (Amp + 1) + (Amp - 1) * cw - sq
    z = np.exp(-1j * 2.0 * np.pi * np.asarray(f) / fs)
    H = (b0 + b1 * z + b2 * z * z) / (a0 + a1 * z + a2 * z * z)
    return 20.0 * np.log10(np.abs(H))


def makeup_db(f, fs, p):
    """OdMakeup's own log-magnitude, from a dict of its constants.  `hf_gain_db` is the mix-keyed
    peak's gain ALREADY resolved for the capture's clean fraction (the stage cannot see the mix;
    `PedalChain` reads `LevelBlend::cleanFraction()` into it)."""
    d = np.full(np.shape(f), float(p["gainDb"]))
    if p["lowCutDb"]:
        d += rbj_shelf_db(f, fs, p["lowHz"], -p["lowCutDb"], p["lowS"], high=False)
    if p["highCutDb"]:
        d += rbj_shelf_db(f, fs, p["highHz"], -p["highCutDb"], p["highS"], high=True)
    if p.get("hf_gain_db"):
        d += F.rbj_peak_db(f, fs, p["hfHz"], p["hfQ"], p["hf_gain_db"])
    return d


def shipped_makeup():
    """Parse OdMakeup's constants out of FitParams.h — never transcribed (s146's masterTaperBreak
    trap: a name that survives a MEANING change silently rebuilds the wrong curve)."""
    import re
    src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)),
                            "..", "src", "dsp", "FitParams.h")).read()
    want = {"gainDb": "odMakeupDb", "lowHz": "odMakeupLowHz", "lowCutDb": "odMakeupLowCutDb",
            "highHz": "odMakeupHighHz", "highCutDb": "odMakeupHighCutDb",
            "lowS": "odMakeupLowS", "highS": "odMakeupHighS",
            "hfHz": "odMakeupHfHz", "hfQ": "odMakeupHfQ",
            "hfAtOdDb": "odMakeupHfAtOdDb", "hfPeakDb": "odMakeupHfPeakDb",
            "hfPeakCf": "odMakeupHfPeakCf", "hfAtCleanDb": "odMakeupHfAtCleanDb"}
    out = {}
    for k, name in want.items():
        m = re.search(rf"\b{name}\s*=\s*(-?[0-9.eE+-]+)\s*;", src)
        if not m:
            die("BH0", f"cannot parse {name} out of FitParams.h — if it was renamed, update THIS "
                       f"parser rather than letting the gate fall back to a stale literal")
        out[k] = float(m.group(1))
    return out


def apply_arm(p, arm):
    """The arm's `--fit` overrides applied to the parsed shipped set, so the Python model and the
    render cannot disagree about what an arm IS."""
    q = dict(p)
    name = {"odMakeupDb": "gainDb", "odMakeupLowCutDb": "lowCutDb", "odMakeupHighCutDb": "highCutDb",
            "odMakeupHighHz": "highHz", "odMakeupLowHz": "lowHz",
            "odMakeupHfAtOdDb": "hfAtOdDb", "odMakeupHfPeakDb": "hfPeakDb",
            "odMakeupHfAtCleanDb": "hfAtCleanDb"}
    for a in arm:
        if "=" in a:
            k, v = a.split("=", 1)
            if k in name:
                q[name[k]] = float(v)
    return q


def hf_gain_at(p, cf):
    """The mix-keyed peak's gain at clean fraction `cf` — the piecewise-linear law of s173."""
    if cf <= p["hfPeakCf"]:
        t = cf / max(p["hfPeakCf"], 1e-9)
        return p["hfAtOdDb"] + t * (p["hfPeakDb"] - p["hfAtOdDb"])
    t = (cf - p["hfPeakCf"]) / max(1.0 - p["hfPeakCf"], 1e-9)
    return p["hfPeakDb"] + t * (p["hfAtCleanDb"] - p["hfPeakDb"])


# ================================================================================================
def bh0_membership(out):
    print("-- BH0: membership, and it is ASSERTED rather than discovered ------------------------")
    missing = [f for _, f, _, _ in CONDITIONS if not os.path.exists(os.path.join(C.CAPTURE_DIR, f))]
    if missing:
        die("BH0", f"missing captures: {missing}")
    if not os.path.exists(os.path.join(C.CAPTURE_DIR, CLEAN_CONTROL)):
        die("BH0", f"missing CLEAN control {CLEAN_CONTROL}")
    by_grunt, by_mix = {}, {}
    for _, _, gr, mx in CONDITIONS:
        by_grunt[gr] = by_grunt.get(gr, 0) + 1
        by_mix[mx] = by_mix.get(mx, 0) + 1
    print(f"    {len(CONDITIONS)} conditions x {len(RUNGS)} rungs x {len(ARMS)} arms")
    print(f"    GRUNT: {by_grunt}    MIX: {by_mix}")
    if len(by_grunt) < 3:
        die("BH0", "the GRUNT axis is not covered at all three positions — every capture without a "
                   "`grunt-` token is GRUNT=cut (s151), so a single-position read is the default "
                   "failure mode here, not an unlucky one")
    print(f"    rungs {RUNGS}; `sweep_clean` excluded — see BH0c")
    out["bh0"] = {"n_conditions": len(CONDITIONS), "rungs": list(RUNGS),
                  "by_grunt": by_grunt, "by_mix": by_mix, "arms": list(ARMS)}


def bh0c_clean_rung(out):
    print("\n-- BH0c: why `sweep_clean` is excluded (a measurement, not a convenience) ------------")
    n_ped = n_mod = 0
    for _, fname, _, _ in CONDITIONS:
        g, ped, mod = curves(fname, "sweep_clean", ())
        n_ped += geom(g, ped) is not None
        n_mod += geom(g, mod) is not None
    print(f"    at `sweep_clean` the estimator resolves the null on ND in {n_ped}/{len(CONDITIONS)} "
          f"conditions and on the MODEL in {n_mod}/{len(CONDITIONS)}")
    if n_mod > n_ped:
        die("BH0c", "the model resolves MORE clean-stimulus cells than ND — that contradicts "
                    "GATE AE and this exclusion needs re-deriving before the gate is trusted")
    print(f"    ⇒ reproduces GATE AE (s133): the model carries no drive-generated feature here at "
          f"clean stimulus.  A rung one side cannot read cannot enter an ordering.")
    out["bh0c"] = {"clean_resolved_pedal": n_ped, "clean_resolved_model": n_mod}


def bh1a_transfer_known_answer(out):
    """The Python OdMakeup model must reproduce what the RENDER does.

    Bleed-free (LEVEL max AND BLEND max, GATE K2's only corner) the composite IS the OD branch, so
    render(ship) - render(makeup off) in dB is the stage's transfer EXACTLY, with no fit and no
    free parameter.  ⚠ This validates the Python model against the shipped C++ — it is the check
    that licenses BH3's arithmetic, and without it BH3 is an argument rather than a measurement."""
    print("\n-- BH1a: the OD-branch transfer, Python model vs the RENDER (bleed-free) -------------")
    fname = "level-1700_base-od.wav"
    g, _, mod_ship = curves(fname, PLAYING_RUNG, ())
    _, _, mod_off = curves(fname, PLAYING_RUNG, HF_OFF + MK_OFF)
    p = shipped_makeup()
    cf = 0.0                                     # bleed-free: LEVEL and BLEND both max
    p = dict(p, hf_gain_db=hf_gain_at(p, cf))
    band = (g >= 200.0) & (g <= 12000.0)
    pred = makeup_db(g[band], A.SAMPLE_RATE if hasattr(A, "SAMPLE_RATE") else 48000.0, p)
    meas = (mod_ship - mod_off)[band]
    # Both curves are shape-normalised, so a constant offset between them is removed by
    # construction and only the SHAPE is comparable — de-mean both, and say so.
    resid = (meas - np.mean(meas)) - (pred - np.mean(pred))
    rms = float(np.sqrt(np.mean(resid ** 2)))
    print(f"    200 Hz-12 kHz, shape-only (both de-meaned): rms |render - python| = {rms:.3f} dB, "
          f"worst {np.max(np.abs(resid)):.3f} dB   n={band.sum()}")
    ok = rms < 0.25
    print(f"    ⇒ {'PASS' if ok else 'REFUSE'} — the Python OdMakeup model {'reproduces' if ok else 'does NOT reproduce'} "
          f"the shipped stage, so BH3's arithmetic is {'licensed' if ok else 'NOT licensed'}")
    if not ok:
        die("BH1a", "the Python transfer model disagrees with the render; BH3 would be narration")
    out["bh1a"] = {"rms_db": rms, "n": int(band.sum())}


def bh1b_synthetic(out):
    """The estimator must recover an INJECTED ordering, and must invent nothing at zero.

    ⚠ The zero rung is the arm's own mutation control (s133): a reader that reports a monotone
    ordering on three copies of one curve is reading noise, not a dose-response."""
    print("\n-- BH1b: synthetic control — injected depths, including ZERO ------------------------")
    g, _, mod = curves("ref-od.wav", PLAYING_RUNG, HF_OFF + MK_OFF)
    f0 = 5600.0
    rows = []
    for inj in ((0.0, 0.0, 0.0), (12.0, 6.0, 3.0), (3.0, 6.0, 12.0)):
        depths = []
        for a in inj:
            d = mod + (F.rbj_peak_db(g, 48000.0, f0, 4.0, -a) if a else 0.0)
            r = geom(g, d)
            depths.append(None if r is None else r["depth_point"])
        rows.append((inj, depths, mono_falling(depths)))
        print(f"    injected {str(inj):>20s} -> read "
              f"{'/'.join('  --' if x is None else f'{x:5.2f}' for x in depths)}   "
              f"monotone-falling {mono_falling(depths)}")
    if rows[1][2] is not True:
        die("BH1b", "a DESCENDING injected ladder did not read as monotone falling — the estimator "
                    "cannot order what it is being asked to order")
    if rows[2][2] is True:
        die("BH1b", "an ASCENDING injected ladder read as monotone FALLING — the statistic is not "
                    "tracking the injected ordering")
    print("    ⇒ PASS — the estimator recovers an injected ordering and does not manufacture one")
    out["bh1b"] = [{"injected": list(i), "read": d, "mono": m} for i, d, m in rows]


def bh1c_clean_control(out):
    """At BLEND = 0 the OD branch is out of circuit, so EVERY arm must be bit-identical.

    A free known answer: it proves the arms reach only what they should.  ⚠ It is also the
    non-vacuity check's partner — an arm that moves nothing anywhere would pass this trivially,
    which is why BH2 separately requires the arms to MOVE the graded statistic."""
    print("\n-- BH1c: CLEAN control — every arm bit-identical at BLEND = 0 -----------------------")
    import hashlib
    hashes = {}
    for arm_name, arm in ARMS.items():
        path = render_of(CLEAN_CONTROL, arm)
        hashes[arm_name] = hashlib.sha256(open(path, "rb").read()).hexdigest()[:16]
        print(f"    {arm_name:14s} {hashes[arm_name]}")
    if len(set(hashes.values())) != 1:
        die("BH1c", "the arms differ at BLEND = 0 — an OD-branch stage is reaching the clean path")
    print("    ⇒ PASS — 0.000e+00, the OD branch is genuinely out of circuit there")
    out["bh1c"] = {"identical": True, "sha": list(hashes.values())[0]}


def bh2_ordering(out):
    """THE HEADLINE.  ND's depth falls monotonically with stimulus; does the model's?"""
    print("\n-- BH2: THE ORDERING — depth vs stimulus (-18 / -12 / -6 dBFS) ----------------------")
    print("    ⚠ DEPTHS ARE PRINTED FOR CONTEXT AND ARE NOT GRADED (§1: no reference has authority")
    print("      over this null's depth).  The graded statistic is the ORDER alone.")
    kept, dropped = matched_cells(ORDER_GRADED, "condition")
    print(f"    MATCHED membership: {len(kept)}/{len(CONDITIONS)} conditions readable by ND AND")
    print(f"    every arm at all {len(RUNGS)} rungs.  Dropped and NAMED: {dropped if dropped else 'none'}")
    if not kept:
        die("BH2", "no condition is readable by every arm — nothing is comparable")
    hdr = f"    {'condition':22s}{'ND':>24s}" + "".join(f"{a:>26s}" for a in ARMS)
    print(hdr)
    depths, mono = {}, {"ND": []}
    for a in ARMS:
        mono[a] = []
    refused = {k: 0 for k in ["ND"] + list(ARMS)}
    for label, fname, _, _ in [c for c in CONDITIONS if c[0] in kept]:
        line = f"    {label:22s}"
        for side in ["ND"] + list(ARMS):
            v = []
            for sw in RUNGS:
                g, ped, mod = curves(fname, sw, () if side == "ND" else ARMS[side])
                r = geom(g, ped if side == "ND" else mod)
                if r is None:
                    refused[side] += 1
                v.append(None if r is None else r["depth_point"])
            depths[(label, side)] = v
            m = mono_falling(v)
            mono[side].append(m)
            s = "/".join("  --" if x is None else f"{x:5.1f}" for x in v)
            line += f"{s + (' OK' if m else ' ..'):>24s}" if side == "ND" else \
                    f"{s + (' OK' if m else ' ..'):>26s}"
        print(line)

    print(f"\n    {'side':14s}{'monotone-falling':>18s}{'refused cells':>15s}{'exact p':>12s}")
    res = {}
    for side in ["ND"] + list(ARMS):
        vals = [m for m in mono[side] if m is not None]
        k, n = sum(vals), len(vals)
        p = binom_tail(k, n, 1.0 / 6.0) if n else float("nan")
        res[side] = {"k": k, "n": n, "p": p, "refused": refused[side]}
        print(f"    {side:14s}{f'{k}/{n}':>18s}{refused[side]:>15d}{p:>12.2e}")
    print("    (exact binomial tail against P(monotone falling | random order) = 1/6 — no bar,")
    print("     no fitted threshold; 3 rungs give exactly 6 orderings and 1 of them is falling)")

    if res["ND"]["k"] < res["ND"]["n"]:
        print(f"\n    ⚠ ND is NOT monotone in {res['ND']['n'] - res['ND']['k']} condition(s) — the")
        print(f"      reference ordering is a measurement, not an assumption, and it is reported")
        print(f"      as measured.  Those conditions still count against every arm equally.")

    moved = [a for a in ARMS if a != BASELINE_ARM
             and any(depths[(l, a)] != depths[(l, BASELINE_ARM)] for l in kept)]
    if len(moved) != len(ARMS) - 1:
        die("BH2", f"an arm did not move the graded statistic anywhere — VACUOUS "
                   f"(moved: {moved}); a --fit that never reaches the DSP reads as a clean result")
    print(f"    non-vacuity: all {len(moved)} non-baseline arms move the statistic ✓")

    # COMPUTED verdict — derived from the counts, never narrated (s128).
    nd_k, ship_k = res["ND"]["k"], res[BASELINE_ARM]["k"]
    best = max((a for a in ARMS), key=lambda a: res[a]["k"])
    print()
    if ship_k >= nd_k:
        print(f"    ⇒ VERDICT: the shipped build MATCHES ND's ordering ({ship_k}/{res[BASELINE_ARM]['n']} "
              f"vs {nd_k}/{res['ND']['n']}) — there is no ordering defect to chase.")
    else:
        print(f"    ⇒ VERDICT: the shipped build does NOT reproduce ND's ordering "
              f"({ship_k}/{res[BASELINE_ARM]['n']} against ND's {nd_k}/{res['ND']['n']}); the best "
              f"arm is '{best}' at {res[best]['k']}/{res[best]['n']}.")
    out["bh2"] = {"per_side": res, "best_arm": best,
                  "depths": {f"{l}|{s}": v for (l, s), v in depths.items()}}
    return res, depths


def bh3_mechanism(out, depths):
    """The lever, and it is arithmetic on the shipped constants — validated by BH1a.

    Prediction: the rung at which the null is deepest moves UP the stimulus ladder as the
    OD-branch gain AT THE NULL rises.  Graded as a RANK correlation over the arms, which needs no
    threshold and no fitted model."""
    print("\n-- BH3: the mechanism — OD-branch gain AT the null vs which rung is deepest ---------")
    p0 = shipped_makeup()
    f_null = 5500.0
    print(f"    {'arm':14s}{'gain @5.5kHz':>14s}{'deepest rung (mode over conditions)':>40s}")
    rows = []
    for arm_name, arm in ARMS.items():
        p = apply_arm(p0, arm)
        # cf at the listening condition, from the stage's own reference point
        p = dict(p, hf_gain_db=hf_gain_at(p, p["hfPeakCf"]))
        gdb = float(makeup_db(np.array([f_null]), 48000.0, p)[0])
        idx = []
        for (label, side), v in depths.items():
            if side != arm_name or any(x is None for x in v):
                continue
            idx.append(int(np.argmax(v)))
        mode = max(set(idx), key=idx.count) if idx else -1
        rows.append((arm_name, gdb, mode))
        print(f"    {arm_name:14s}{gdb:14.2f}{RUNGS[mode] + f'  (n={len(idx)})':>40s}")
    gains = [r[1] for r in rows]
    modes = [r[2] for r in rows]
    # Spearman by hand (n=4): rank correlation, exact and threshold-free to state.
    def rank(v):
        o = np.argsort(v)
        r = np.empty(len(v))
        r[o] = np.arange(len(v))
        return r
    rg, rm = rank(gains), rank(modes)
    rho = float(np.corrcoef(rg, rm)[0, 1]) if len(set(modes)) > 1 else float("nan")
    print(f"\n    rank correlation (gain at the null, deepest rung) over {len(rows)} arms: "
          f"rho = {rho:+.3f}")
    if np.isnan(rho):
        print("    ⇒ NOT MEASURABLE — every arm peaks at the same rung, so the axis does not move")
    elif rho > 0:
        print("    ⇒ CONSISTENT — more OD-branch gain at the null pushes the depth peak to a")
        print("      LOUDER rung, which is what an |OD| = |clean| crossing must do.")
        print(f"    ⭐ s173 adds {rows[0][1] - rows[2][1]:+.2f} dB at 5.5 kHz over the s172 shelf, and")
        print("      that is the whole of the change: HALVING the high-shelf cut (6.0 -> 3.0 dB)")
        print("      and adding a peak centred 5600 Hz, i.e. ON the null.")
    else:
        print("    ⇒ REFUTED — the depth peak does not track the OD-branch gain at the null; the")
        print("      mechanism stated in this gate's docstring is wrong and must be rewritten.")
    out["bh3"] = {"f_null_hz": f_null, "rows": [{"arm": a, "gain_db": g, "deepest": RUNGS[m]}
                                                for a, g, m in rows], "rho": rho}


def bh4_centre(out):
    """The OTHER axis: the null's CENTRE, which is what s173 changed these constants to fix.

    ⛔ An ordering fix that gives back GATE BF's centre gain is not a fix — it is a trade, and
    s173's own row records that walk as a USER-REPORTED regression.  Graded as the model/pedal
    centre ratio at the playing rung, the same form BF5/BF6 use."""
    print("\n-- BH4: the CENTRE axis — no candidate may give back GATE BF's gain ------------------")
    kept, dropped = matched_cells(ORDER_GRADED, "cell")
    keep_at = [(l, f) for l, f, _, _ in CONDITIONS if (l, PLAYING_RUNG) in kept]
    print(f"    MATCHED membership at {PLAYING_RUNG}: {len(keep_at)}/{len(CONDITIONS)} conditions; "
          f"dropped {[l for l, _, _, _ in CONDITIONS if (l, PLAYING_RUNG) not in kept] or 'none'}")
    print(f"    {'arm':14s}{'median f0 ratio':>18s}{'worst |1-r|':>14s}{'n':>5}")
    res = {}
    for arm_name, arm in ARMS.items():
        rs = []
        for label, fname in keep_at:
            g, ped, mod = curves(fname, PLAYING_RUNG, arm)
            rp, rm = geom(g, ped), geom(g, mod)
            if rp and rm:
                rs.append(rm["f0"] / rp["f0"])
        if not rs:
            die("BH4", f"no readable centre pairs for arm {arm_name}")
        med = float(np.median(rs))
        worst = float(np.max(np.abs(1.0 - np.array(rs))))
        res[arm_name] = {"median_ratio": med, "worst_abs_err": worst, "n": len(rs)}
        print(f"    {arm_name:14s}{med:18.3f}{worst:14.3f}{len(rs):>5}")
    print("    (1.000 = the model's null sits exactly on ND's; GATE BF's own statistic form)")
    out["bh4"] = res
    return res


def bh5_frontier(out, ordering, centre):
    """The deliverable: a FRONTIER, because the two axes are bought against each other."""
    print("\n-- BH5: the JOINT frontier — ordering AND centre, no candidate may buy one with the "
          "other --")
    base_c = centre[BASELINE_ARM]["median_ratio"]
    print(f"    {'arm':14s}{'ordering':>12s}{'centre ratio':>15s}{'centre vs ship':>17s}")
    best = None
    for arm_name in ARMS:
        k, n = ordering[arm_name]["k"], ordering[arm_name]["n"]
        c = centre[arm_name]["median_ratio"]
        dc = abs(1.0 - c) - abs(1.0 - base_c)
        print(f"    {arm_name:14s}{f'{k}/{n}':>12s}{c:15.3f}{dc:+17.3f}")
        if best is None or (k, -abs(1.0 - c)) > best[1]:
            best = (arm_name, (k, -abs(1.0 - c)))
    nd_k = ordering["ND"]["k"]
    dominating = [a for a in ARMS
                  if ordering[a]["k"] >= nd_k
                  and abs(1.0 - centre[a]["median_ratio"]) <= abs(1.0 - base_c)]
    print()
    if dominating:
        print(f"    ⇒ A DOMINATING CANDIDATE EXISTS: {dominating} — matches ND's ordering AND does")
        print(f"      not regress the centre.  That is a shippable candidate, not merely a trade.")
    else:
        print(f"    ⇒ NO DOMINATING CANDIDATE among the arms tested: every arm that reaches ND's")
        print(f"      ordering ({nd_k}/{ordering['ND']['n']}) gives back centre accuracy, and every")
        print(f"      arm that keeps the centre fails the ordering.  ⇒ the two axes are IN TENSION")
        print(f"      on this family, and closing item 17 needs a term the current constants cannot")
        print(f"      express — NOT a re-tune of them.  ⛔ Do not ship a revert on the strength of")
        print(f"      the ordering column alone; s173's walk was a user-reported regression.")
    out["bh5"] = {"dominating": dominating, "best": best[0] if best else None,
                  "baseline_centre": base_c}


def bh6_bass_depth(out):
    """The ~40-60 Hz BASS null, whose DEPTH *is* gradeable — unlike the treble one.

    Why this one gets a depth grade and the treble one does not: §3's LF row records HW at 18 Hz
    against ND at 35 Hz (grunt boost) and, at attack boost, the same frequency with **ND ~10 dB
    DEEPER**.  So at this null hardware wants SHALLOWER than ND — the two references agree on the
    DIRECTION, and a model deeper than ND is moving away from both.  That is the one place in
    item 17 where a depth target is licensed at all, and it is licensed only as a direction
    (§5 rule 3: sign and order of magnitude, never a fit target — §3 is a PNG read and s170
    established the images are off disk)."""
    print("\n-- BH6: the ~40-60 Hz BASS null — depth, where a DIRECTION is licensed --------------")
    print("    §3 LF row: HW 18 Hz vs ND 35 Hz (grunt boost); at attack boost the same frequency")
    print("    with ND ~10 dB DEEPER ⇒ hardware wants SHALLOWER than ND here.  Both references")
    print("    therefore agree on the direction, which the 320 Hz null's licence does NOT.")
    kept, dropped = matched_cells(DEPTH_GRADED, "cell")
    print()
    print(f"    MATCHED membership: {len(kept)}/{len(CONDITIONS) * len(RUNGS)} (condition, rung) "
          f"cells readable by ND AND every arm.")
    print(f"    ⚠ The unmatched form is what a first draft printed and it is INVALID here: an arm")
    print(f"      whose null is too SHALLOW to read drops that cell, and shallow is the outcome")
    print(f"      being scored, so unmatched pooling rewards exactly the arms it should penalise.")
    if dropped:
        drops = sorted({l for l, _ in dropped})
        print(f"    dropped conditions (NAMED, never hidden): {drops}")
    if not kept:
        die("BH6", "no cell is readable by every arm — nothing is comparable")
    print()
    print(f"    {'condition':22s}{'rung':10s}{'ND':>8s}" + "".join(f"{a:>13s}" for a in ARMS))
    err = {a: [] for a in ARMS}
    invar = {"ND": [], **{a: [] for a in ARMS}}
    for label, fname, _, _ in CONDITIONS:
        per_side = {}
        for sw in [r for r in RUNGS if (label, r) in kept]:
            line = f"    {label:22s}{sw.replace('sweep_', ''):10s}"
            g, ped, _ = curves(fname, sw, ())
            rp = geom(g, ped, DEPTH_GRADED)
            line += f"{rp['depth_point']:8.2f}" if rp else f"{'--':>8s}"
            per_side.setdefault("ND", []).append(rp["depth_point"] if rp else None)
            for a, arm in ARMS.items():
                gg, _, mod = curves(fname, sw, arm)
                rm = geom(gg, mod, DEPTH_GRADED)
                per_side.setdefault(a, []).append(rm["depth_point"] if rm else None)
                line += f"{rm['depth_point']:13.2f}" if rm else f"{'--':>13s}"
                if rp and rm:
                    err[a].append(rm["depth_point"] - rp["depth_point"])
            print(line)
        for side, v in per_side.items():
            good = [x for x in v if x is not None]
            if len(good) == len(RUNGS) and all((label, r) in kept for r in RUNGS):
                invar[side].append(max(good) - min(good))

    print(f"\n    {'arm':14s}{'median (model-ND)':>20s}{'mean |err|':>13s}{'n':>5}"
          f"{'deeper than ND':>17s}")
    res = {}
    for a in ARMS:
        e = np.array(err[a])
        if not len(e):
            die("BH6", f"no readable bass-notch pairs for arm {a}")
        deeper = int(np.sum(e > 0))
        res[a] = {"median": float(np.median(e)), "mean_abs": float(np.mean(np.abs(e))),
                  "n": len(e), "deeper_than_nd": deeper}
        print(f"    {a:14s}{np.median(e):20.2f}{np.mean(np.abs(e)):13.2f}{len(e):>5}"
              f"{f'{deeper}/{len(e)}':>17s}")

    # The LF dose-response.  MONOTONE in the lever is the claim; it is counted, not asserted.
    print(f"\n    LF dose-response — `odMakeupLowCutDb` against the model's own bass depth:")
    ship_low = shipped_makeup()["lowCutDb"]
    # ⚠ MATCHED across the ladder too, for the same reason: a rung of the ladder that reads fewer
    # cells is not a smaller number, it is a different question.
    def readable_at_every_rung_of_ladder(fname):
        for _, arm in LOWCUT_LADDER:
            g, _, mod = curves(fname, PLAYING_RUNG, arm)
            if geom(g, mod, DEPTH_GRADED) is None:
                return False
        return True

    lad_keep = [(l, f) for l, f, _, _ in CONDITIONS if readable_at_every_rung_of_ladder(f)]
    ladder = []
    for val, arm in LOWCUT_LADDER:
        name = f"{ship_low:.1f} (shipped)" if val is None else ("makeup OFF" if val == float("inf")
                                                                else f"{val:.1f}")
        ds = []
        for label, fname in lad_keep:
            g, ped, mod = curves(fname, PLAYING_RUNG, arm)
            rm = geom(g, mod, DEPTH_GRADED)
            if rm:
                ds.append(rm["depth_point"])
        ladder.append((name, float(np.median(ds)), len(ds)))
        print(f"      lowCutDb = {name:16s} median model depth {np.median(ds):6.2f} dB   n={len(ds)}")
    med = [m for _, m, _ in ladder]
    mono = all(med[i] > med[i + 1] for i in range(len(med) - 1))
    print(f"      ⇒ monotone DECREASING in the lever: {mono}  "
          f"({'the lever is real and single-signed' if mono else 'NOT monotone — do not size a fix from it'})")

    # Stimulus invariance: ND's bass depth barely moves with stimulus.  A model whose does is
    # carrying a mechanism ND does not — a free second axis on the same renders.
    print(f"\n    stimulus SPAN of the depth (max-min over the three rungs), median over conditions:")
    for side in ["ND"] + list(ARMS):
        v = invar[side]
        print(f"      {side:14s} {np.median(v):5.2f} dB   n={len(v)}")

    base = res[BASELINE_ARM]
    best = min(ARMS, key=lambda a: res[a]["mean_abs"])
    print()
    if base["deeper_than_nd"] > base["n"] / 2 and base["median"] > 0:
        print(f"    ⇒ VERDICT: the shipped build's bass null is DEEPER than ND in "
              f"{base['deeper_than_nd']}/{base['n']} readings (median {base['median']:+.2f} dB).")
        print(f"      §3 puts hardware SHALLOWER than ND here, so that is away from BOTH references.")
        print(f"      Closest arm on this axis: '{best}' at mean |err| {res[best]['mean_abs']:.2f} dB")
        print(f"      against the shipped {base['mean_abs']:.2f}.")
    else:
        print(f"    ⇒ VERDICT: the shipped build's bass null is NOT systematically deeper than ND "
              f"({base['deeper_than_nd']}/{base['n']}, median {base['median']:+.2f} dB) — no defect "
              f"on this axis.")
    out["bh6"] = {"per_arm": res, "lowcut_ladder": ladder, "lowcut_monotone": bool(mono),
                  "stimulus_span": {k: float(np.median(v)) for k, v in invar.items() if v}}


def main():
    ap = argparse.ArgumentParser(description="GATE BH — HF null depth-vs-stimulus ORDERING")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()

    print(__doc__.split("Run:")[0].strip()[:0] or "", end="")
    print("=" * 96)
    print("GATE BH — the HF cancellation null's DEPTH-vs-STIMULUS ORDERING  (s178, open item 17)")
    print("=" * 96)
    print("⚠ §1 gives NEITHER reference authority over this null's DEPTH, so depth is printed and")
    print("  never graded.  What is graded is the ORDERING, which is threshold-free.")

    out = {}
    bh0_membership(out)
    bh0c_clean_rung(out)
    bh1a_transfer_known_answer(out)
    bh1b_synthetic(out)
    bh1c_clean_control(out)
    ordering, depths = bh2_ordering(out)
    bh3_mechanism(out, depths)
    centre = bh4_centre(out)
    bh5_frontier(out, ordering, centre)
    bh6_bass_depth(out)

    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(out, fh, indent=1)
        print(f"\nwrote {args.json}")
    print("\n" + "=" * 96)


if __name__ == "__main__":
    main()
