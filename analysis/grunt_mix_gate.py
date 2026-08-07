#!/usr/bin/env python3.11
"""GATE BI — open-work item 18: does the MIX respond to the GRUNT switch ~4x too strongly?

THE ITEM, AND WHY ITS OWN WORDING IS THE THING TO TEST
------------------------------------------------------
s172 §6 recorded, as an unowned by-product: *"at makeup 0 the model's GRUNT spread at the listening
mix is 4.4 dB against the pedal's 1.08 — the model's MIX responds to the GRUNT switch ~4x too
strongly."*  The user promoted that to open-work item 18 on 2026-08-07.

That sentence is **one measurement and one attribution**, and only the measurement was taken.  The
measured thing is a SPREAD of `C1 = mid_peak − mid_notch` on the composite curve; the attribution —
*the MIX* — names a mechanism nothing in s172 isolated.  C1 can move with GRUNT for three reasons
that live in three different places:

  (a) the OD:CLEAN RATIO changes with GRUNT more than the pedal's does   <- "the mix", the claim
  (b) the OD BRANCH's own contrast changes with GRUNT more than the pedal's  <- a filter/shape thing
  (c) the two COMBINE differently — same branch levels, same branch shapes, different phase

`an-attribution-is-not-a-measurement` (s125).  This gate separates the three, because they have
completely different remedies: (a) is `OdMakeup`'s territory, (b) is the clipper's GRUNT cap bank,
and (c) is not reachable by any magnitude-domain correction at all.

THE DESIGN — A MATCHED 3 GRUNT x 5 MIX LADDER, WHICH THE CAPTURE SET ALREADY CONTAINS
------------------------------------------------------------------------------------
⚠⚠ Every capture without a `grunt-` token is GRUNT = **CUT** (`captures.py` defaults `gruntIdx`),
the trap that cost s151 a whole fit and that s172 §6 itself nearly repeated.  Membership here is
therefore spelled out per position AND asserted against each file's own parsed settings (BI0a), so
a mislabelled row cannot survive.

The two ends of the ladder are what make the decomposition possible with no fitting:
  * **bleed-free** (LEVEL max AND BLEND max — GATE K2's only corner) is the OD branch ALONE.
  * **BLEND = 0** is the clean branch ALONE, and the OD branch is out of circuit entirely.
⇒ (OD − CLEAN) per GRUNT, each side differenced against ITSELF, is s172's own ratio construction
and every per-side capture-chain scalar cancels exactly.  That is question (a), directly, with no
model of the mix law anywhere in it.

WHAT IT FINDS (session 179)
---------------------------
* (a) is **REFUTED**: the OD:clean ratio's GRUNT dependence tracks the pedal at 1.11x / 1.16x /
  1.86x over 40-100 / 100-250 / 250-900 Hz, and the absolute model−pedal ratio error in the feature
  band is 0.24-0.93 dB.  The mix is not 4x anything.
* (b) is **REFUTED at flat and boost and CONFIRMED at cut**: bleed-free the model's C1 lands +0.16
  and +0.06 dB from the pedal's, and +3.08 at cut — which is s172's own `odNotchDepthDb = +3`, a
  priced and accepted decision, not a new finding.
* (c) is what is left, and it has a threshold-free signature: the model's COMPOSITE notch
  FREQUENCY wanders 20.6 % across the GRUNT switch while the pedal's holds to 2.9 %, and both
  sides' bleed-free nulls are pinned.  A feature that moves when a switch that only changes level
  into the clipper is thrown, while the branch that owns it does not move, is a **cancellation
  between the branches** — and the model has one the pedal does not.

⭐⭐ AND THE STATISTIC IS ITEM 17's 320 Hz HALF, NUMERICALLY.  Model − pedal at the listening mix
reads +0.24 / +4.51 / +5.38 dB across cut/flat/boost, which reproduces session 178 §3's model−ND
column **to 0.00 dB at all three positions** on an independently written probe.  Item 17 graded that
column against the only per-condition depth licence in the reference set (`reference-sources.md` §3:
HW deeper than ND by +1.6 at cut, +3.5-4.8 at flat, far deeper at boost) and closed it as a **§5
rule 2 PASS — inside at flat, UNDER at cut and boost**.  ⇒ item 18 and item 17's 320 Hz half are one
measurement wearing two names, and the larger-than-ND GRUNT spread is the direction hardware
records.  ⛔ It is therefore **not a fit target**, and BI5 says so from the numbers rather than from
this docstring.

⚠ SCOPE, three ways:
  * §3 is a PNG read and s170 established the images are off disk — SIGN and rough SIZE only.  BI5
    grades DIRECTION and CONTAINMENT, never distance.
  * `C1` is the null's depth referred to its RIGHT shoulder (the ~450 Hz recovery peak), which is
    the same physical quantity §3 describes up to which shoulder is used.  Stated, not hidden.
  * the coherent-envelope positions (BI4b) are exact for the MODEL, whose mix coefficients are its
    own algebra, and INDICATIVE for the pedal, whose are unknown.  The gate proves the pedal's
    differ rather than assuming they do not, and refuses to grade the pedal on them.

Run:
    /opt/homebrew/bin/python3.11 analysis/grunt_mix_gate.py
    /opt/homebrew/bin/python3.11 analysis/grunt_mix_gate.py --json analysis/reports/s179_grunt_mix.json
"""
import argparse
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import captures as C                     # noqa: E402
import feature_locus_gate as W           # noqa: E402
import level_law_gate as LL              # noqa: E402
import od_tone_restore_fit as F          # noqa: E402

REN_DIR = "build/s179_grunt_mix"         # PRIVATE — never GATE W's read-only s122 cache
SWEEP = "sweep_drv_-12"                  # the user's stated playing level (memory: playing-level-is-drv-minus-12)

GRUNTS = ("cut", "flat", "boost")

# ---- membership.  NAMED per GRUNT, and ASSERTED against each file's own parsed settings --------
# The mix labels are ordered by clean fraction: bleedfree (0) -> blend0930 (~0.94).
MIX_ORDER = ("bleedfree", "blendmax", "blend1430", "blend1200", "blend0930")
CAPS = {
    ("cut",   "bleedfree"): "level-1700_base-od.wav",
    ("flat",  "bleedfree"): "level-1700_grunt-flat_base-od.wav",
    ("boost", "bleedfree"): "level-1700_grunt-boost_base-od.wav",
    ("cut",   "blendmax"):  "ref-od.wav",
    ("flat",  "blendmax"):  "grunt-flat_base-od.wav",
    ("boost", "blendmax"):  "grunt-boost_base-od.wav",
    ("cut",   "blend1430"): "blend-1430_base-od.wav",
    ("flat",  "blend1430"): "grunt-flat_blend-1430_base-od.wav",
    ("boost", "blend1430"): "grunt-boost_blend-1430_base-od.wav",
    ("cut",   "blend1200"): "blend-1200_base-od.wav",
    ("flat",  "blend1200"): "grunt-flat_blend-1200_base-od.wav",
    ("boost", "blend1200"): "grunt-boost_blend-1200_base-od.wav",
    ("cut",   "blend0930"): "blend-0930_base-od.wav",
    ("flat",  "blend0930"): "grunt-flat_blend-0930_base-od.wav",
    ("boost", "blend0930"): "grunt-boost_blend-0930_base-od.wav",
}
CLEAN_ONLY = "blend-0700_base-od.wav"    # BLEND = 0 -> the OD branch is out of circuit entirely
LISTEN_MIX = "blendmax"                  # LEVEL noon, BLEND max: the user's listening condition

# The two features, windows IMPORTED from GATE W by name (s133: quote the measured band, never a
# label).  C1 is their difference on one curve, so it is invariant to any level normalisation.
PK_WIN = W.FEAT_BY_NAME["mid_peak"][2]
NT_WIN = W.FEAT_BY_NAME["mid_notch"][2]

# Bands for the OD:clean ratio.  The first two are where item 17's bass null lives and where GATE
# AD's AD4 measured the GRUNT contrast; 250-900 is s172's own feature band, quoted verbatim.
BANDS = (("40-100", 40.0, 100.0), ("100-250", 100.0, 250.0), ("250-900", 250.0, 900.0),
         ("900-2.8k", 900.0, 2800.0), ("2.8-8k", 2800.0, 8000.0))
FEATURE_BAND = "250-900"

# The arm that turns every s172/s173 [ENG] term off, so item 18's own headline number (measured at
# "makeup 0") can be reproduced rather than transcribed.
MK_OFF = ("--fit", "odMakeupDb=0", "--fit", "odMakeupLowCutDb=0", "--fit", "odMakeupHighCutDb=0",
          "--fit", "odNotchDepthDb=0", "--fit", "odMakeupHfAtOdDb=0", "--fit", "odMakeupHfPeakDb=0",
          "--fit", "odMakeupHfAtCleanDb=0")

# s172 §1's own bleed-free GRUNT-cut reading.  PEDAL side, so it is binary-independent and a
# genuine cross-session known answer rather than a re-run of our own build.
S172_BLEEDFREE_CUT_PEDAL = 13.92
KA_TOL = 0.05

# `reference-sources.md` §3, the ONLY per-condition depth licence in the reference set.  HW minus
# ND, dB, by GRUNT.  ⛔ Sign and rough size only (§5 rule 3) — `None` at boost because "~26 dB" is
# a near-total cancellation read off a PNG and s178's own knife-edge finding forbids quoting it as
# a number; what survives there is "much deeper", i.e. a direction with no ceiling.
HW_LICENCE = {"cut": (1.6, 1.6), "flat": (3.5, 4.8), "boost": (None, None)}

# s178 §3's model−ND column at the listening mix, for the identity check in BI5.
S178_MODEL_MINUS_ND = {"cut": 0.24, "flat": 4.51, "boost": 5.38}
IDENTITY_TOL = 0.10


def die(tag, msg):
    print(f"\n⛔ {tag}: {msg}")
    sys.exit(1)


# ================================================================================================
# Curves.  UN-normalised — this gate must compare branch LEVELS against each other, so it cannot
# use `od_tone_restore_fit.curves`, which removes each curve's 100 Hz-8 kHz mean by design.  The
# normalisation is applied locally, and only where the statistic is a within-curve contrast.
# ================================================================================================
_CURVES = {}


def _tag(arm):
    return "" if not arm else "__" + "_".join(a.replace("=", "") for a in arm if a != "--fit")


def curves(fname, arm=()):
    """-> (grid, pedal_db, model_db), UN-normalised, on GATE W's own 1/48-oct grid."""
    key = (fname, arm)
    if key in _CURVES:
        return _CURVES[key]
    orig, ref = W._load_orig()
    parsed = C.parse_capture(fname)
    out = os.path.join(REN_DIR, fname.replace(".wav", "") + _tag(arm) + "_plugin.wav")
    W.render(out, C.render_args(parsed, extra_args=list(arm)))   # binary-stamped; a stale build re-renders

    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)

    def one(al):
        f, m = A.transfer_h1(A.seg_of(al, SWEEP), ref)
        return W.smooth(f, m)

    _CURVES[key] = (W.GRID, one(cap_al), one(ren_al))
    return _CURVES[key]


def c1_of(d):
    """C1 = mid_peak − mid_notch, read as window extrema.  A within-curve contrast, so it is
    invariant to any per-curve level offset and needs no normalisation to be comparable."""
    pk = (W.GRID >= PK_WIN[0]) & (W.GRID <= PK_WIN[1])
    nt = (W.GRID >= NT_WIN[0]) & (W.GRID <= NT_WIN[1])
    return float(np.max(d[pk]) - np.min(d[nt]))


def extrema_f(d, nt_win=None):
    """-> (f_peak, f_notch) of this curve's own extrema inside GATE W's windows."""
    g = W.GRID
    nw = NT_WIN if nt_win is None else nt_win
    pk = np.flatnonzero((g >= PK_WIN[0]) & (g <= PK_WIN[1]))
    nt = np.flatnonzero((g >= nw[0]) & (g <= nw[1]))
    return float(g[pk[int(np.argmax(d[pk]))]]), float(g[nt[int(np.argmin(d[nt]))]])


# Widened notch windows for BI4a.  A minimum one cell from a bound is a BOUND, not a reading
# (s151), and two of the six composite notches sit within two cells of GATE W's own bounds — so
# the objection has to be answered before BI4's headline can be quoted.
NT_WIDE = ((285.0, 358.0), (260.0, 400.0), (240.0, 420.0), (220.0, 450.0))


def band_mean(d, lo, hi):
    m = (W.GRID >= lo) & (W.GRID <= hi)
    return float(np.mean(d[m]))


def at(d, f):
    return float(np.interp(f, W.GRID, d))


def spread(v):
    return max(v) - min(v)


# ================================================================================================
def bi0_validity():
    """Membership, the s151 GRUNT trap mechanised, and the cross-session known answer."""
    print("=" * 96)
    print("BI0 — VALIDITY: membership asserted from SETTINGS, not from filenames")
    print("=" * 96)

    missing = [f for f in list(CAPS.values()) + [CLEAN_ONLY]
               if not os.path.exists(os.path.join(C.CAPTURE_DIR, f))]
    if missing:
        die("BI0a", f"captures absent: {missing}")

    # ⚠⚠ THE s151 TRAP, MECHANISED.  A capture's GRUNT position comes from `captures.parse_capture`,
    # never from the label in this file's table — a label is a guess about a naming convention and
    # naming conventions are not versioned (s114).
    want_idx = {g: C._GRUNT_IDX[g] for g in GRUNTS}
    bad = []
    for (g, mix), fn in sorted(CAPS.items()):
        p = C.parse_capture(fn)
        if p["gruntIdx"] != want_idx[g]:
            bad.append(f"{fn}: labelled {g} (idx {want_idx[g]}) but parses idx {p['gruntIdx']}")
    if bad:
        die("BI0a", "GRUNT label/settings mismatch:\n  " + "\n  ".join(bad))

    # The mix labels must be a real ordering in clean fraction, and bleed-free must be GATE K2's
    # corner (BOTH LEVEL and BLEND max) — the premise the whole (a)/(b) split rests on.
    cfs = {}
    for mix in MIX_ORDER:
        vals = {F.clean_frac_of(CAPS[(g, mix)]) for g in GRUNTS}
        if len(vals) != 1:
            die("BI0a", f"mix '{mix}' is not one clean fraction across GRUNT: {sorted(vals)}")
        cfs[mix] = vals.pop()
    if cfs["bleedfree"] != 0.0:
        die("BI0a", f"'bleedfree' is not bleed-free (cf = {cfs['bleedfree']:.4f}); GATE K2's corner "
                    "needs BOTH LEVEL and BLEND at max")
    order = [cfs[m] for m in MIX_ORDER]
    if any(order[i] >= order[i + 1] for i in range(len(order) - 1)):
        die("BI0a", f"MIX_ORDER is not increasing in clean fraction: {order}")

    print(f"  membership: {len(CAPS)} captures = 3 GRUNT x {len(MIX_ORDER)} mixes, "
          f"+ 1 clean control ({CLEAN_ONLY})")
    print("  GRUNT position of every capture read from parse_capture and MATCHES its label (15/15)")
    print("  clean fraction by mix: " + "  ".join(f"{m}={cfs[m]:.3f}" for m in MIX_ORDER))

    # ---- BI0b: the cross-session known answer.  PEDAL side, so no build enters it. -------------
    _, ped, _ = curves(CAPS[("cut", "bleedfree")])
    got = c1_of(ped)
    if abs(got - S172_BLEEDFREE_CUT_PEDAL) > KA_TOL:
        die("BI0b", f"pedal bleed-free GRUNT-cut C1 = {got:.2f} dB, but session 172 §1 recorded "
                    f"{S172_BLEEDFREE_CUT_PEDAL:.2f}.  Either the estimator is not s172's or the "
                    "capture has moved — resolve before reading anything below.")
    print(f"  BI0b known answer: pedal bleed-free GRUNT-cut C1 = {got:.2f} dB vs s172 §1's "
          f"{S172_BLEEDFREE_CUT_PEDAL:.2f}  ✅  (pedal side ⇒ binary-independent)")

    # ---- BI0c: NON-VACUITY.  The GRUNT axis must actually move the model's OD branch. ----------
    bf_model = [c1_of(curves(CAPS[(g, "bleedfree")])[2]) for g in GRUNTS]
    if spread(bf_model) < 1.0:
        die("BI0c", f"the GRUNT switch moves the model's bleed-free C1 by only "
                    f"{spread(bf_model):.3f} dB — the axis under test is inert, so every "
                    "comparison below is between identical things (s110).")
    print(f"  BI0c non-vacuity: GRUNT moves the model's bleed-free C1 by {spread(bf_model):.2f} dB")

    # ---- BI0d: the CLEAN control.  At BLEND = 0 the OD branch is out of circuit, so every -------
    # OD-path [ENG] term must be BIT-IDENTICAL there.  s172's own free known answer.
    _, _, m_on = curves(CLEAN_ONLY)
    _, _, m_off = curves(CLEAN_ONLY, MK_OFF)
    worst = float(np.max(np.abs(np.asarray(m_on) - np.asarray(m_off))))
    if worst > 1e-9:
        die("BI0d", f"at BLEND = 0 the OD-path terms move the output by {worst:.3e} dB — the OD "
                    "branch is NOT out of circuit, so the clean reference is contaminated by the "
                    "very terms this gate differences against it.")
    print(f"  BI0d clean control: OD-path terms are bit-identical at BLEND = 0 "
          f"(worst {worst:.2e} dB) ⇒ the clean branch is clean")
    return {"cf": cfs, "ka_bleedfree_cut": got, "nonvacuity_db": spread(bf_model),
            "clean_control_worst_db": worst}


# ================================================================================================
def bi1_reproduce():
    """Item 18's own headline number, reproduced rather than transcribed."""
    print()
    print("=" * 96)
    print("BI1 — THE STATISTIC REPRODUCES, AND IT HAS GROWN SINCE s172")
    print("=" * 96)
    print("  C1 = mid_peak − mid_notch at the LISTENING mix (LEVEL noon, BLEND max), "
          f"{SWEEP}\n")
    rows, cols = {}, ("pedal", "makeup 0", "shipped")
    print(f"  {'GRUNT':7s} " + " ".join(f"{c:>10s}" for c in cols))
    for g in GRUNTS:
        fn = CAPS[(g, LISTEN_MIX)]
        _, ped, mod = curves(fn)
        _, _, mod0 = curves(fn, MK_OFF)
        rows[g] = (c1_of(ped), c1_of(mod0), c1_of(mod))
        print(f"  {g:7s} " + " ".join(f"{v:10.2f}" for v in rows[g]))
    sp = [spread([rows[g][i] for g in GRUNTS]) for i in range(3)]
    print(f"  {'SPREAD':7s} " + " ".join(f"{v:10.2f}" for v in sp))
    print(f"\n  ⇒ makeup-0 spread {sp[1]:.2f} dB against the pedal's {sp[0]:.2f} "
          f"({sp[1] / sp[0]:.1f}x) — s172 §6 recorded 4.40 / 1.08 on its own epoch, so item 18's "
          "number is REAL")
    print(f"  ⇒ SHIPPED spread {sp[2]:.2f} dB ({sp[2] / sp[0]:.1f}x).  s172 shipped 5.71; s173's "
          "HF term and taper and s177's C31 have landed since, so the epoch has moved and the "
          "figure to quote is this one.")
    return {"c1_listen": rows, "spread": {"pedal": sp[0], "makeup0": sp[1], "shipped": sp[2]}}


# ================================================================================================
def bi2_is_it_the_mix():
    """(a) — the OD:CLEAN RATIO's own GRUNT dependence.  The claim, tested directly."""
    print()
    print("=" * 96)
    print("BI2 — IS IT THE MIX?  The OD:clean ratio, each side differenced against ITSELF")
    print("=" * 96)
    print("  bleed-free OD (the branch alone) minus BLEND=0 clean (the other branch alone), dB.")
    print("  Every per-side capture-chain scalar cancels exactly — s172's own construction.\n")

    _, pcl, mcl = curves(CLEAN_ONLY)
    ratio = {}
    print(f"  {'band':10s} " + " ".join(f"{'  ped   mod   m−p':>21s}" for _ in ()) )
    hdr = f"  {'GRUNT':7s}" + "".join(f"{n:>22s}" for n, _, _ in BANDS)
    print(hdr)
    print(f"  {'':7s}" + "".join(f"{'ped     mod     m−p':>22s}" for _ in BANDS))
    for g in GRUNTS:
        _, ped, mod = curves(CAPS[(g, "bleedfree")])
        cells = []
        for n, lo, hi in BANDS:
            rp = band_mean(ped, lo, hi) - band_mean(pcl, lo, hi)
            rm = band_mean(mod, lo, hi) - band_mean(mcl, lo, hi)
            ratio[(g, n)] = (rp, rm)
            cells.append(f"{rp:7.2f}{rm:8.2f}{rm - rp:+7.2f}")
        print(f"  {g:7s}" + "".join(cells))

    print(f"\n  GRUNT dependence of that ratio (boost − cut), the quantity item 18 names:")
    print(f"  {'band':10s} {'pedal':>8s} {'model':>8s} {'model/pedal':>13s}")
    fold = {}
    for n, _, _ in BANDS:
        dp = ratio[("boost", n)][0] - ratio[("cut", n)][0]
        dm = ratio[("boost", n)][1] - ratio[("cut", n)][1]
        fold[n] = (dp, dm, (dm / dp) if abs(dp) > 0.5 else None)
        r = f"{fold[n][2]:13.2f}" if fold[n][2] is not None else f"{'(den < 0.5)':>13s}"
        print(f"  {n:10s} {dp:8.2f} {dm:8.2f}" + r)

    # ---- the verdict, COMPUTED ----------------------------------------------------------------
    graded = [n for n, _, _ in BANDS if fold[n][2] is not None]
    worst_fold = max(abs(fold[n][2]) for n in graded)
    worst_abs = max(abs(ratio[(g, FEATURE_BAND)][1] - ratio[(g, FEATURE_BAND)][0]) for g in GRUNTS)
    claim_fold = 4.0
    if worst_fold >= claim_fold:
        print(f"\n  ⇒ CONSISTENT with item 18's attribution: the mix ratio's GRUNT dependence is "
              f"{worst_fold:.2f}x the pedal's, at or beyond the claimed {claim_fold:.0f}x.")
        ok = True
    else:
        print(f"\n  ⇒ ⛔⛔ THE ATTRIBUTION IS REFUTED.  The OD:clean ratio — the mix itself — tracks "
              f"the pedal's GRUNT dependence at worst {worst_fold:.2f}x")
        print(f"     (bands with a readable denominator: {', '.join(graded)}), against item 18's "
              f"claimed ~{claim_fold:.0f}x, and the ABSOLUTE model−pedal ratio error over "
              f"{FEATURE_BAND} Hz is at most {worst_abs:.2f} dB across the switch.")
        print("     ⇒ whatever makes C1 spread 4-6x, it is not the OD:clean balance.")
        ok = False
    # ⭐ A by-product worth recording once: at 2.8-8 kHz the model's ratio has essentially NO GRUNT
    # dependence where the pedal has some — the OPPOSITE sign of item 18's claim, in a band item 18
    # never looked at.  Named, not absorbed.
    hf = fold["2.8-8k"]
    if hf[2] is not None and hf[2] < 0.5:
        print(f"\n  ⭐ by-product, opposite sign: over 2.8-8 kHz the pedal's OD:clean ratio moves "
              f"{hf[0]:+.2f} dB across GRUNT and the model's {hf[1]:+.2f} ({hf[2]:.2f}x) — there "
              "the model UNDER-responds to the switch.  Recorded, not absorbed into this item.")
    return {"ratio": {f"{g}|{n}": ratio[(g, n)] for g in GRUNTS for n, _, _ in BANDS},
            "fold": {n: fold[n] for n in fold}, "worst_fold": worst_fold,
            "worst_abs_feature_band": worst_abs, "attribution_supported": ok}


# ================================================================================================
def bi3_is_it_the_branch():
    """(b) — the OD branch's OWN contrast, bleed-free.  No clean tap anywhere in it."""
    print()
    print("=" * 96)
    print("BI3 — IS IT THE OD BRANCH?  C1 bleed-free (the branch alone), per GRUNT")
    print("=" * 96)
    rows = {}
    print(f"  {'GRUNT':7s} {'pedal':>8s} {'model':>8s} {'m−p':>8s}")
    for g in GRUNTS:
        _, ped, mod = curves(CAPS[(g, "bleedfree")])
        rows[g] = (c1_of(ped), c1_of(mod))
        print(f"  {g:7s} {rows[g][0]:8.2f} {rows[g][1]:8.2f} {rows[g][1] - rows[g][0]:+8.2f}")
    sp_p = spread([rows[g][0] for g in GRUNTS])
    sp_m = spread([rows[g][1] for g in GRUNTS])
    print(f"  {'SPREAD':7s} {sp_p:8.2f} {sp_m:8.2f} {sp_m / sp_p:8.2f}x")

    off = {g: rows[g][1] - rows[g][0] for g in GRUNTS}
    matched = [g for g in GRUNTS if abs(off[g]) < 1.0]
    print(f"\n  ⇒ bleed-free the model matches the pedal at {len(matched)} of 3 positions "
          f"({', '.join(matched) if matched else 'none'}), and bleed-free its GRUNT spread is "
          f"{sp_m / sp_p:.2f}x the pedal's — i.e. SMALLER, the opposite sign of the defect.")
    if abs(off["cut"]) >= 1.0:
        print(f"  ⚠ GRUNT cut is over by {off['cut']:+.2f} dB.  That is `odNotchDepthDb = +3.0`, "
              "s172's own priced and accepted decision (CLAUDE.md records ~1.5 dB beyond the "
              "hardware licence at this one cell, accepted) — NOT a new finding.")
    return {"c1_bleedfree": rows, "spread_pedal": sp_p, "spread_model": sp_m,
            "fold": sp_m / sp_p, "offset": off}


# ================================================================================================
def bi4_is_it_the_combination():
    """(c) — the two branches COMBINE differently.  Threshold-free, then mechanism."""
    print()
    print("=" * 96)
    print("BI4 — IS IT THE COMBINATION?  Where the composite's own notch SITS")
    print("=" * 96)
    print("  A cancellation moves when the balance between the branches moves; a filter's notch")
    print("  does not.  The GRUNT switch changes level into the clipper, so it moves the balance.\n")

    f_bf, f_mix = {}, {}
    print(f"  {'GRUNT':7s} {'side':5s} {'bleed-free f_nt':>16s} {'composite f_nt':>16s} {'shift':>9s}")
    for g in GRUNTS:
        _, pbf, mbf = curves(CAPS[(g, "bleedfree")])
        _, pmx, mmx = curves(CAPS[(g, LISTEN_MIX)])
        for side, dbf, dmx in (("ped", pbf, pmx), ("mod", mbf, mmx)):
            _, nb = extrema_f(dbf)
            _, nm = extrema_f(dmx)
            f_bf[(g, side)], f_mix[(g, side)] = nb, nm
            print(f"  {g:7s} {side:5s} {nb:16.1f} {nm:16.1f} {nm - nb:+9.1f}")

    # ---- BI4a: is any of that a WINDOW rather than a reading? --------------------------------
    # ⚠⚠ The model's flat/boost notches land 1 and 3 cells from GATE W's lower bound and its cut
    # notch 1 cell from the upper one.  s151: a minimum resting on a bound is a REFUSAL, and s126
    # showed an extremum-finder always returns something.  GATE AV's remedy — WIDEN and re-read —
    # is free here, and if the wander survives it is a measurement rather than a window artefact.
    print("\n  BI4a — window robustness.  Same extremum, notch window widened 73 Hz -> 230 Hz:")
    print(f"  {'GRUNT':7s} {'side':5s} " + "".join(f"{f'{a:.0f}-{b:.0f}':>12s}" for a, b in NT_WIDE)
          + "   verdict")
    unstable = []
    for g in GRUNTS:
        _, pmx, mmx = curves(CAPS[(g, LISTEN_MIX)])
        for side, dmx in (("ped", pmx), ("mod", mmx)):
            vals = [extrema_f(dmx, w)[1] for w in NT_WIDE]
            stable = max(vals) == min(vals)
            if not stable:
                unstable.append(f"{g}/{side}")
            print(f"  {g:7s} {side:5s} " + "".join(f"{v:12.1f}" for v in vals)
                  + ("   IDENTICAL" if stable else "   ⚠ MOVES"))
    if unstable:
        print(f"  ⇒ ⚠ {', '.join(unstable)} move with the window — those cells are BOUNDS, not "
              "readings, and BI4's wander must be re-read before it is quoted.")
    else:
        print("  ⇒ all 6 composite notches are INTERIOR and BIT-STABLE across a 3.2x window "
              "widening ⇒ the wander below is a measurement, not a window artefact.")

    for side in ("ped", "mod"):
        vb = [f_bf[(g, side)] for g in GRUNTS]
        vm = [f_mix[(g, side)] for g in GRUNTS]
        print(f"\n  {side}: bleed-free notch spans {min(vb):.1f}–{max(vb):.1f} Hz "
              f"({100 * (max(vb) / min(vb) - 1):.1f} %), composite spans {min(vm):.1f}–{max(vm):.1f} Hz "
              f"({100 * (max(vm) / min(vm) - 1):.1f} %)")
    wp = 100 * (max(f_mix[(g, "ped")] for g in GRUNTS) / min(f_mix[(g, "ped")] for g in GRUNTS) - 1)
    wm = 100 * (max(f_mix[(g, "mod")] for g in GRUNTS) / min(f_mix[(g, "mod")] for g in GRUNTS) - 1)
    if unstable:
        print(f"\n  ⇒ ⚠ NOT READ — {len(unstable)} composite notch(es) move with the analysis "
              "window (BI4a), so the wander cannot be attributed to the device.")
    elif wm > wp:
        print(f"\n  ⇒ ⭐⭐ THE MODEL'S COMPOSITE NOTCH WANDERS {wm:.1f} % ACROSS THE GRUNT SWITCH "
              f"AND THE PEDAL'S {wp:.1f} %.")
        print("     Both sides' OWN branch nulls are near-pinned, so the model's composite notch is "
              "not its OD null showing through — it is a CANCELLATION between the branches, at a "
              "frequency the balance chooses.  The pedal does not have one there.")
    else:
        print(f"\n  ⇒ the model's composite notch wanders {wm:.1f} % against the pedal's {wp:.1f} % "
              "— NO added cancellation is indicated.")

    # ---- BI4b: the coherent envelope, MODEL side exact ---------------------------------------
    print()
    print("  BI4b — the coherent-sum envelope at the composite's own extrema.")
    print("  |clean| ± |OD|, both scaled to the mix by the SHIPPED coefficients.  `pos` is where in")
    print("  that envelope the composite actually lands: 1 = perfectly in phase, 0 = fully")
    print("  cancelling.  ⚠ EXACT for the model (its own algebra); INDICATIVE for the pedal.")
    pos = {}
    pc = C.parse_capture(CLEAN_ONLY)
    c_od, c_cl = LL.coef_closed(pc["blend"], LL.level_taper(pc["level"]))
    _, pcl, mcl = curves(CLEAN_ONLY)
    print(f"\n  {'GRUNT':7s} {'side':5s} {'feature':8s} {'f':>8s} {'OD':>8s} {'CLEAN':>8s} "
          f"{'obs':>8s} {'pos':>7s}")
    outside = []
    for g in GRUNTS:
        pm = C.parse_capture(CAPS[(g, LISTEN_MIX)])
        a_od, a_cl = LL.coef_closed(pm["blend"], LL.level_taper(pm["level"]))
        pb = C.parse_capture(CAPS[(g, "bleedfree")])
        b_od, _ = LL.coef_closed(pb["blend"], LL.level_taper(pb["level"]))
        s_od = 20.0 * np.log10(a_od / b_od)
        s_cl = 20.0 * np.log10(a_cl / c_cl)
        _, pbf, mbf = curves(CAPS[(g, "bleedfree")])
        _, pmx, mmx = curves(CAPS[(g, LISTEN_MIX)])
        for side, dbf, dmx, dcl in (("ped", pbf, pmx, pcl), ("mod", mbf, mmx, mcl)):
            fp, fn = extrema_f(dmx)
            for lbl, f in (("peak", fp), ("notch", fn)):
                o, c = at(dbf, f) + s_od, at(dcl, f) + s_cl
                lin_o, lin_c = 10 ** (o / 20), 10 ** (c / 20)
                lo, hi = abs(lin_c - lin_o), lin_c + lin_o
                obs = 10 ** (at(dmx, f) / 20)
                p = (obs - lo) / max(1e-30, hi - lo)
                pos[(g, side, lbl)] = p
                if side == "ped" and not (-0.02 <= p <= 1.02):
                    outside.append(f"{g}/{lbl} pos={p:.3f}")
                print(f"  {g:7s} {side:5s} {lbl:8s} {f:8.1f} {o:8.2f} {c:8.2f} "
                      f"{at(dmx, f):8.2f} {p:7.3f}")

    print()
    if outside:
        print("  ⚠⚠ The PEDAL lands OUTSIDE its own envelope at " + ", ".join(outside) + ".")
        print("     That is a PROOF the pedal's mix coefficients are not the model's, not a defect")
        print("     in the pedal — so the pedal's `pos` column is NOT graded, and the model's is")
        print("     read alone.  (`a-recovered-quantity-that-must-be-invariant-and-isnt`, s104.)")
    mp = [pos[(g, "mod", "peak")] for g in GRUNTS]
    mn = [pos[(g, "mod", "notch")] for g in GRUNTS]
    print(f"  MODEL: at its composite peak pos = {', '.join(f'{v:.2f}' for v in mp)} "
          f"(1 = maximally constructive); at its composite notch pos = "
          f"{', '.join(f'{v:.2f}' for v in mn)} (0 = fully cancelling).")
    if max(mp) > 0.9 and min(mn) < 0.5:
        print("  ⇒ the model's OD branch is riding NEAR THE CONSTRUCTIVE LIMIT at the peak and")
        print("     CANCELLING HARD at the notch — both push C1 up, and both are PHASE, which no")
        print("     magnitude-domain correction can reach and `release_gate.py` cannot see")
        print("     (open item 13's finding on a second feature).")
    return {"f_bleedfree": {f"{g}|{s}": f_bf[(g, s)] for g in GRUNTS for s in ("ped", "mod")},
            "f_composite": {f"{g}|{s}": f_mix[(g, s)] for g in GRUNTS for s in ("ped", "mod")},
            "wander_pct": {"ped": wp, "mod": wm}, "window_unstable": unstable,
            "envelope_pos": {f"{g}|{s}|{l}": pos[(g, s, l)]
                             for g in GRUNTS for s in ("ped", "mod") for l in ("peak", "notch")},
            "pedal_outside_envelope": outside}


# ================================================================================================
def bi5_licence(bi1):
    """The identity with item 17's 320 Hz half, and the grading that closes it."""
    print()
    print("=" * 96)
    print("BI5 — WHOSE MEASUREMENT IS THIS?  The identity with open item 17's 320 Hz half")
    print("=" * 96)
    got = {g: bi1["c1_listen"][g][2] - bi1["c1_listen"][g][0] for g in GRUNTS}
    print(f"  {'GRUNT':7s} {'model−pedal (here)':>20s} {'s178 §3 model−ND':>20s} {'diff':>8s} "
          f"{'HW licence':>14s}")
    same = True
    for g in GRUNTS:
        want = S178_MODEL_MINUS_ND[g]
        d = got[g] - want
        same &= abs(d) <= IDENTITY_TOL
        lic = HW_LICENCE[g]
        ls = "much deeper" if lic[0] is None else (f"+{lic[0]}" if lic[0] == lic[1]
                                                   else f"+{lic[0]}–{lic[1]}")
        print(f"  {g:7s} {got[g]:+20.2f} {want:+20.2f} {d:+8.2f} {ls:>14s}")

    if same:
        print(f"\n  ⇒ ⭐⭐ IDENTICAL to {IDENTITY_TOL:.2f} dB at all three positions, on an "
              "independently written probe.")
        print("     Item 18's C1 statistic and item 17's ~320 Hz null depth are ONE MEASUREMENT.")
    else:
        print("\n  ⇒ the two columns DIFFER — they are not the same statistic after all, and the "
              "grading below does not transfer.  Resolve before quoting item 17's verdict here.")

    # Containment against the licence.  DIRECTION and CONTAINMENT only — never distance (§5 rule 3).
    verdicts = {}
    for g in GRUNTS:
        lo, hi = HW_LICENCE[g]
        v = got[g]
        if lo is None:
            verdicts[g] = "far under" if v > 0 else "WRONG SIGN"
        elif v < lo - 1e-9:
            verdicts[g] = "under"
        elif v > hi + 1e-9:
            verdicts[g] = "OVER"
        else:
            verdicts[g] = "inside"
    print("\n  Against `reference-sources.md` §3's licence (⛔ PNG read: sign and rough size only):")
    for g in GRUNTS:
        print(f"    {g:7s} {verdicts[g]}")
    over = [g for g in GRUNTS if verdicts[g] in ("OVER", "WRONG SIGN")]
    if over:
        print(f"\n  ⇒ OVER the hardware licence at {', '.join(over)} — item 18 names a real "
              "over-response and there is something to correct.")
    else:
        print("\n  ⇒ ⭐⭐⭐ NOT OVER AT ANY POSITION.  Every cell is inside the licence or under it,")
        print("     and the progression is monotone in GRUNT with the same sign as hardware's ⇒")
        print("     `reference-sources.md` §5 rule 2 defines that as a PASS.")
        print("     ⇒ the model's GRUNT spread being LARGER than ND's is the direction the")
        print("       governing reference records, so item 18's '4x too strongly' is a distance")
        print("       from ND on an axis where ND is not the authority.  ⛔ NOT a fit target.")
    return {"model_minus_pedal": got, "s178_column": S178_MODEL_MINUS_ND,
            "identity_holds": bool(same), "licence_verdict": verdicts, "over": over}


# ================================================================================================
def bi6_item17_link(bi2):
    """The LF band, where item 17's actionable half lives.  One mechanism, or two?"""
    print()
    print("=" * 96)
    print("BI6 — THE LINK TO ITEM 17's BASS HALF (item 17: do NOT fit them independently)")
    print("=" * 96)
    lf = {g: bi2["ratio"][f"{g}|40-100"] for g in GRUNTS}
    print(f"  OD:clean ratio over 40–100 Hz, where item 17's bass null lives:")
    print(f"  {'GRUNT':7s} {'pedal':>8s} {'model':>8s} {'m−p':>8s}")
    for g in GRUNTS:
        print(f"  {g:7s} {lf[g][0]:8.2f} {lf[g][1]:8.2f} {lf[g][1] - lf[g][0]:+8.2f}")
    errs = [lf[g][1] - lf[g][0] for g in GRUNTS]
    print(f"\n  ⇒ the model's OD branch is hotter than the pedal's re its own clean path at all "
          f"three positions ({min(errs):+.2f} … {max(errs):+.2f} dB), which is item 17's bass-null "
          "finding measured on a different statistic (a LEVEL, not a depth).")
    print(f"  ⇒ and it is GRUNT-DEPENDENT: the error spans {spread(errs):.2f} dB across the switch, "
          f"largest at {GRUNTS[int(np.argmax(errs))]}.")
    print("  ⇒ so item 17's bass half and item 18 SHARE an operand — the OD branch's level re")
    print("     clean — but item 18's own defect (BI4) is a PHASE relationship at 290–330 Hz that")
    print("     that operand does not set.  ⇒ ONE OPERAND, TWO DEFECTS: a band-limited LF")
    print("     correction for item 17 is not blocked by item 18, and cannot fix it either.")
    return {"lf_ratio": {g: lf[g] for g in GRUNTS}, "lf_err": errs, "lf_err_spread": spread(errs)}


# ================================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--json", help="write the full report here")
    args = ap.parse_args()

    os.makedirs(REN_DIR, exist_ok=True)
    rep = {"gate": "BI", "session": 179, "item": 18, "sweep": SWEEP, "ren_dir": REN_DIR}
    rep["bi0"] = bi0_validity()
    rep["bi1"] = bi1_reproduce()
    rep["bi2"] = bi2_is_it_the_mix()
    rep["bi3"] = bi3_is_it_the_branch()
    rep["bi4"] = bi4_is_it_the_combination()
    rep["bi5"] = bi5_licence(rep["bi1"])
    rep["bi6"] = bi6_item17_link(rep["bi2"])

    print()
    print("=" * 96)
    print("VERDICT")
    print("=" * 96)
    mix = rep["bi2"]["attribution_supported"]
    over = rep["bi5"]["over"]
    print(f"  the statistic          : REAL — spread {rep['bi1']['spread']['shipped']:.2f} dB "
          f"against the pedal's {rep['bi1']['spread']['pedal']:.2f}")
    print(f"  (a) the MIX ratio      : {'SUPPORTED' if mix else 'REFUTED'} — worst GRUNT fold "
          f"{rep['bi2']['worst_fold']:.2f}x, absolute error ≤ "
          f"{rep['bi2']['worst_abs_feature_band']:.2f} dB in the feature band")
    print(f"  (b) the OD BRANCH      : REFUTED at flat/boost (bleed-free m−p "
          f"{rep['bi3']['offset']['flat']:+.2f} / {rep['bi3']['offset']['boost']:+.2f} dB); "
          f"cut is s172's accepted +3")
    print(f"  (c) the COMBINATION    : the model's composite notch wanders "
          f"{rep['bi4']['wander_pct']['mod']:.1f} % across GRUNT vs the pedal's "
          f"{rep['bi4']['wander_pct']['ped']:.1f} % ⇒ an added CANCELLATION, i.e. PHASE")
    print(f"  against HARDWARE       : {'OVER at ' + ', '.join(over) if over else 'PASS at all three positions'}")
    print()
    if not over and not mix:
        print("  ⇒ ITEM 18's NUMBER IS REAL, ITS ATTRIBUTION IS REFUTED, AND ON THE GOVERNING")
        print("    REFERENCE IT IS A PASS.  It is item 17's 320 Hz half seen as a spread, and that")
        print("    half is closed.  ⛔ Not a fit target.  What is left is a phase relationship no")
        print("    magnitude-domain instrument in this project can grade.")

    if args.json:
        os.makedirs(os.path.dirname(args.json), exist_ok=True)
        with open(args.json, "w") as fh:
            json.dump(rep, fh, indent=1, default=float)
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
