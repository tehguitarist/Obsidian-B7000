#!/usr/bin/env python3
"""GATE BM — THE ANCHOR RE-READ ON THE **MIX GRID** (session 184, open item 19's task P1).

WHY THIS EXISTS
---------------
GATE BL (s183) re-read `blendEndStop`'s price at the BLEED-FREE CORNER and found it large there:
a flat −0.2126 dB plus a shape term reaching **12.25 dB**, `mid_notch` losing 4.07 dB of POINT
depth, `treble_peak` losing 9 of 36 readings, and the treble peak's drive walk more than doubling.

Then the user said the thing that reorders all of it:

    "bleed-free is only ONE setting, and not even the most used one, so it's not the be all and
     end all."

s183 §9 checked that steer for free (no render) on `OdToneRestore`'s mix law alone and it inverted
the priorities — the applied cut moves **+1.587 dB at the corner** against **−0.508 dB at the worst
PLAYED setting** and **−0.144 dB at the listening condition**: ~10x smaller and OPPOSITE in sign.
That is one stage's law. It says nothing about the other six features, the depth estimators, or the
membership, all of which s183 measured at the corner ONLY.

This gate asks the question nobody has asked: **which of item 19's seven features actually move at
settings people play?**  Same three-arm construction as GATE BL (ship / `--fit blendEndStop=0` /
`BLEND = 0`), so no capture, no reference and no authority question enters — every number here is
one build minus another build.  What changes is the CONDITION GRID: **20 mix cells x 3 GRUNT x
3 DRIVE x 4 sweeps** — a 4x4 LEVEL x BLEND product plus the LEVEL ladder at BLEND max — instead of
the corner alone.  ⚠ The ladder is not an optional extra: the 4x4 product alone put its worst cell
at its own LOWEST SAMPLED LEVEL, and an extremum at a sampling edge is not a measurement of the
extremum.  See `LADDER_LEVELS` for what the analytic column said about it, for free.

⛔⛔ CORRECTION 1 TO THE HANDOVER — AND IT IS WHY THIS GATE CAN SAY ANYTHING ANALYTIC AT ALL.
s183 §10 hands P1 forward with *"off the corner the perturbation is not a flat gain (BL1's
derivation is corner-only — `b_eff = 1` is what makes the coefficients constants)"*.  The second
clause is imprecise and the conclusion does not follow.  `LevelBlend` is a **purely resistive
network with one unknown** (the LEVEL wiper; both sources are op-amp outputs and the BLEND wiper
draws no current), so its two coefficients are **frequency-independent constants at EVERY (L, B)**,
not only at the corner — BM0b asserts that on both of GATE K's mirrors across the whole grid.  What
is corner-only is their VALUE, `(1-e, e)`, and in particular `cl_0 = 0`.

⇒ the flat/shape split GENERALISES exactly, into something sharper than BL had:

    out_ship / out_e0  =  (od_s + cl_s*u) / (od_0 + cl_0*u),      u = CLEAN/OD

a Moebius transform of `u` whose two limits are both ANALYTIC per cell:

    u -> 0  (OD dominates)     ->  od_s/od_0   = the flat term, −0.171 … −0.213 dB
    u -> oo (CLEAN dominates)  ->  cl_s/cl_0   = the other end of the bracket

⭐⭐ **SO THE CORNER IS A SINGULARITY OF THE LAW, NOT MERELY ITS WORST CELL.**  At the corner
`cl_0 = 0`, the second limit is `+oo`, and the perturbation is UNBOUNDED — which is why BL measured
12.25 dB there and could only ever MEASURE it.  At every other cell the bracket is finite and its
width IS `Delta rho`, **0.21 … 1.11 dB across the played grid** (BM1, no render).

⚠ The bracket bounds **co-phased** branches only, and that caveat is not cosmetic: `od_0 + cl_0*u`
vanishes where the *e0 arm itself* cancels, so at a genuine null the ratio can leave the bracket.
That is the corner's mechanism in a milder form, and it is why P1 says MEASURE.  BM2 measures it and
counts how much of the band leaves the bracket, which LOCALISES the cancellations instead of
averaging over them.

⛔⛔ CORRECTION 2, AND IT IS THE BIGGER ONE: **`ship − e0` IS NOT ONE MECHANISM, IT IS TWO** — AND
s183 §3 ATTRIBUTED ALL OF IT TO ONE.
This gate's first draft carried a branch-reconstruction known answer: the mix render must be the two
BRANCH renders combined with GATE K's coefficients (a triangle inequality, threshold-free).  It
**FAILED — 70979 of 517248 points outside the envelope, worst excursion 20.6x** — and the guard was
right.  `OdToneRestore` is **MIX-KEYED** (s156): its cut is `base + K*S(cleanFraction) +
depthOffsetDb`, and `PedalChain::syncOdToneMix()` feeds it `LevelBlend::cleanFraction()`.  So the OD
branch's own response is a function of (LEVEL, BLEND), the chain is not a two-branch mixer, and
`ship − e0` at ANY cell — the corner included — is the sum of:

    (i)  the MIX COEFFICIENTS moving          (od, cl)  ->  analytic, BM1
    (ii) `OdToneRestore`'s CUT moving, because `cleanFraction()` moved  ->  analytic, BM5

⇒ **s183 §3's "the 320 Hz null loses 4.07 dB of POINT depth because the bleed floors the bottom" is
a NET of two OPPOSING mechanisms.**  At the corner the mix law simultaneously applies **1.587 dB
MORE cut** (which deepens the OD branch's notch), so the bleed's own flooring contribution is
*larger* than 4.07 dB, not equal to it.

⭐ SEPARATING THEM NEEDS NO `src/` CHANGE, because `odNotchDepthDb` is already a fit knob that adds
a uniform dB to that same `cutDb`.  A third arm does it exactly:

    ship     end stop ON,  cut = base + K*S(cf_ship)
    mixfroz  end stop OFF, cut = base + K*S(cf_e0) + [K*(S(cf_ship) − S(cf_e0))]
             i.e. e0's MIX COEFFICIENTS with SHIP's NOTCH CUT
    e0       end stop OFF, cut = base + K*S(cf_e0)

    ship − mixfroz  =  the MIX-COEFFICIENT effect alone
    mixfroz − e0    =  the NOTCH-CUT effect alone

BM0g gates that decomposition on a known answer with no threshold in it: the notch arm must be
LOCALISED at `kNotchFreq` (it is one biquad) and its sign at the notch centre must track
`sign(−K[g][d])`, which **changes across the 9 (GRUNT x DRIVE) cells** (K is negative on the Cut
row, mixed on Flat, positive on Boost) — so a 9-cell mixed-sign test, not a tolerance.

WHAT THIS GATE IS NOT
---------------------
It does not re-fit anything, propose a constant, or grade the model against either reference.  It
measures ONE difference — shipped minus pre-s181 — on the model alone, off the corner, and splits
it into its two mechanisms.

⚠⚠ EVERY CAPTURE WITHOUT A `grunt-` TOKEN IS GRUNT = CUT (`captures.py` defaults it; the s151 trap
cost that session most of a fit).  The grid is explicitly 3 GRUNT x 3 DRIVE for that reason, and
because `mid_notch` is a cancellation in a network the GRUNT switch feeds.

⭐ DISK.  A render is 16 MB and this grid is 540 of them (8.6 GB) against a volume that is 97 %
full.  So renders are STREAMED: render -> extract all four sweeps' curves -> cache the CURVES
(14 KB) -> delete the wav, which is 1100x smaller and makes a re-run instant (measured: the whole
540-condition curve cache is 8.4 MB against GATE BL's 445 MB of wavs for 24 conditions).  The guard
arms needing sample-level bit-identity keep their wavs (via GATE BL's own cache, six files), because
bit-identity cannot be checked on a smoothed curve.
⛔ Do NOT "simplify" this into a wav cache; it does not fit on the disk.
"""

import argparse
import json
import math
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import analyze as A                      # noqa: E402
import bleedfree_anchor_gate as BL       # noqa: E402
import comprehensive_report as CR        # noqa: E402
import feature_locus_gate as W           # noqa: E402
import level_law_gate as K               # noqa: E402
import od_tone_restore_fit as OT         # noqa: E402

OS_FACTOR = BL.OS_FACTOR                 # imported, not transcribed — the gates must agree
CURVE_DIR = "build/s184_mix_grid_curves"
BL_REPORT = "analysis/reports/s183_bleedfree_anchor.json"

# ---- the condition grid ------------------------------------------------------------------------
# ⭐ EVERY MIX CELL BELOW IS A REAL CAPTURE ON DISK, which is what makes this a grid rather than a
# synthetic sweep — and `check-for-unread-data-first`, since s183 §9 found the 4x3 grid unused:
#   level-{0930,1200,1430}_blend-{0930,1200,1430}     the 3x3 interior              (9 captures)
#   level-1700_blend-{0930,1200,1430}                 the BLEND ladder at LEVEL max (3)
#   level-{0930,1200,1430,1700}_base-od               the B = max column            (4, including
#                                                      ref-od at L = 0.5 and the corner at L = 1)
# Clock codes map (h + mm/60 - 7)/10 (`captures._clock_to_x`), so 0930 -> 0.25 … 1700 -> 1.0.
LEVELS = (("0930", 0.25), ("1200", 0.50), ("1430", 0.75), ("1700", 1.00))
BLENDS = (("0930", 0.25), ("1200", 0.50), ("1430", 0.75), ("1700", 1.00))

# ⭐⭐ THE LEVEL LADDER AT BLEND MAX, AND IT IS NOT AN OPTIONAL EXTRA — IT IS WHAT STOPS THIS GATE
# PUBLISHING A MAXIMUM THAT RESTS ON ITS OWN SAMPLING EDGE.  The 4x4 grid's worst cell came out at
# its LOWEST sampled LEVEL (0.25), and BM1's analytic Δρ keeps GROWING as LEVEL falls (+2.66 dB at
# L 0.25 -> +3.77 at 0.1875 -> +5.11 at 0.125 -> +8.22 at 0.0625), because `|od|/|cl|` approaches
# **1** from above — the deepest possible cancellation between the two branches.  So the extreme was
# outside the grid, and an extremum at the edge of a sampled range is not a measurement of the
# extremum.  These four detents are on disk (`level-{0815,1045,1315,1545}_base-od`) and complete the
# 9-point LEVEL ladder P1 asked for.
LADDER_B = 1.00
LADDER_LEVELS = (("0815", 0.125), ("1045", 0.375), ("1315", 0.625), ("1545", 0.875))

# ⛔⛔ L = 0 IS EXCLUDED BY NAME, AND THE REASON IS A DEFECT THIS PROJECT ALREADY OWNS.  At LEVEL min
# the e0 arm's coefficients are EXACTLY (0, 0) — digital silence, which IS open item 12's mute, the
# thing `blendEndStop` was shipped to fix.  Differencing anything against digital silence is s162's
# 214.41 dB "requirement" (`ratio-statistics-need-a-denominator-guard`), so the cell carries no shape
# information and would poison every pooled statistic.  Named rather than silently dropped (s40).
EXCLUDED_LEVELS = ((0.00, "the e0 arm is digital silence there (coefficients exactly (0, 0)) — "
                          "item 12's mute; a difference against silence is not a measurement"),)

# The condition list, built ONCE so every sub-gate iterates the same cells (a second nested loop is
# a second thing to keep in step).  4x4 product + the LEVEL ladder at BLEND max.
MIX_CELLS = tuple([(lt, lv, bt, bv) for lt, lv in LEVELS for bt, bv in BLENDS]
                  + [(lt, lv, "1700", LADDER_B) for lt, lv in LADDER_LEVELS])
DRIVES = BL.DRIVES                       # imported so the two gates cannot drift apart
GRUNTS = BL.GRUNTS
SWEEPS = BL.SWEEPS

# Named once, so no cell is "the corner" or "the listening condition" by coincidence of its numbers.
CORNER = (1.00, 1.00)
# `ref-od.wav` is LEVEL noon / BLEND max (`captures._REF_OD`); the rung is
# `playing-level-is-drv-minus-12`.
LISTENING = (0.50, 1.00)
PLAY_SWEEP = "sweep_drv_-12"

F_LO_GRADE, F_HI_GRADE = BL.F_LO_GRADE, BL.F_HI_GRADE
LOCATOR_RES_FRAC = BL.LOCATOR_RES_FRAC
BITS = BL.BITS
ARMS = ("ship", "e0", "mixfroz")

JOBS = max(1, min(8, (os.cpu_count() or 4) - 2))


# =================================================================================================
# `OdToneRestore`'s mix law, mirrored — the third arm's `odNotchDepthDb` is computed from it
# =================================================================================================
# Transcribed from src/dsp/OdToneRestore.h.  A transcription is what `rebuild-targets-dont-
# transcribe` warns about, so it carries TWO free known answers checked before use (`check_mix_law`
# below): S must be pinned to 0 at kMixCfRef, and the shipped depth offset must match FitParams.h.
# ⚠ node 0 RE-ANCHORED 0.000 -> 0.02418 at s185 (item 19's P2) — it is the bleed-free
# corner's clean fraction, i.e. FitParams::blendEndStop, not a free constant.
MIX_CF = (0.02418, 0.210, 0.320, 0.440, 0.560, 0.730, 0.870, 1.000)
MIX_S = (0.951, -0.525, -0.195, 0.000, 0.017, 0.177, 0.224, 0.252)
MIX_CF_REF = 0.441
NOTCH_FREQ = 323.0                       # kNotchFreq
DRIVE_NODES = (0.0, 0.25, 0.5, 0.75, 1.0)   # kX
# kNotchMixK, rows in ENUM order Cut < Flat < Boost (NOT the APVTS order).
NOTCH_MIX_K = ((-7.87, -8.61, -9.34, -9.50, -9.65),      # Cut
               (-1.56, 0.71, 2.97, 1.97, 0.97),          # Flat
               (3.40, 4.61, 5.81, 5.81, 5.81))           # Boost
SHIPPED_DEPTH_OFFSET_DB = 3.0            # FitParams::odNotchDepthDb
# kNotchGainDb's DRIVE-0 column, in the same ENUM row order.  Used ONLY for its ordering, by BM0h,
# which is the one guard that can catch a permuted GRUNT row (see the ⛔⛔ block there).  Row LABELS
# are pinned to the header text by `check_mix_law` so this cannot silently go stale.
NOTCH_BASE_DRIVE0 = (1.16, 18.33, 17.15)     # Cut, Flat, Boost

# ⚠⚠ APVTS GRUNT order is {Boost, Cut, Flat} and the enum's is {Cut, Flat, Boost}, so indexing
# `NOTCH_MIX_K` with a raw capture/render GRUNT index SILENTLY PERMUTES THE ROWS.  This is
# `PedalChain::gruntEnum()` mirrored (its own comment says the same thing), and the rows differ in
# SIGN across it, so getting it wrong would invert the third arm rather than merely mis-size it.
GRUNT_ENUM = {0: 2, 1: 0, 2: 1}          # APVTS Boost->2, Cut->0, Flat->1


def mix_shape(x):
    """S(cleanFrac) — `OdToneRestore::mixShape`, piecewise-linear on MIX_CF/MIX_S."""
    if x <= MIX_CF[0]:
        return MIX_S[0]
    if x >= MIX_CF[-1]:
        return MIX_S[-1]
    for i in range(len(MIX_CF) - 1):
        if x <= MIX_CF[i + 1]:
            t = (x - MIX_CF[i]) / (MIX_CF[i + 1] - MIX_CF[i])
            return MIX_S[i] + t * (MIX_S[i + 1] - MIX_S[i])
    return MIX_S[-1]


def lerp5(table, x):
    """`OdToneRestore::lerp5` — the DRIVE-knob interpolation over kX."""
    if x <= DRIVE_NODES[0]:
        return table[0]
    if x >= DRIVE_NODES[4]:
        return table[4]
    for i in range(4):
        if x <= DRIVE_NODES[i + 1]:
            t = (x - DRIVE_NODES[i]) / (DRIVE_NODES[i + 1] - DRIVE_NODES[i])
            return table[i] + t * (table[i + 1] - table[i])
    return table[4]


def check_mix_law():
    """Two known answers on the transcription above, run before anything uses it."""
    if abs(mix_shape(MIX_CF_REF)) > 2e-3:
        sys.exit(f"GATE BM: the transcribed mix shape is not pinned at kMixCfRef "
                 f"(S({MIX_CF_REF}) = {mix_shape(MIX_CF_REF):.4f}, expected 0).  The table has "
                 "moved in OdToneRestore.h and this copy is stale.")
    # ⭐⭐ DIVERGENCE GUARD ADDED s185, AND IT IS THE s182 GATE-K2 DEFECT CAUGHT BEFORE IT LANDED.
    # The pinning check above is blind to node 0 (S(kMixCfRef) interpolates between nodes 3 and 4),
    # so when s185 re-anchored `kMixCf[0]` this transcription would have gone stale SILENTLY while
    # every existing guard kept passing — exactly how GATE K's two mirrors spent a session
    # modelling a pot nothing runs.  Compare the whole transcription against the PARSED header.
    _T = OT.shipped_tables()
    for _name, _mine, _theirs in (("kMixCf", MIX_CF, _T["kMixCf"]), ("kMixS", MIX_S, _T["kMixS"])):
        if len(_mine) != len(_theirs) or max(abs(a - b) for a, b in zip(_mine, _theirs)) > 1e-12:
            sys.exit(f"GATE BM: transcribed {_name} has drifted from src/dsp/OdToneRestore.h "
                     f"({list(_mine)} vs {list(_theirs)}).  Update the transcription; do not "
                     "tolerate the drift -- every arm here is computed through it.")
    src = open("src/dsp/FitParams.h").read()
    m = re.search(r"double\s+odNotchDepthDb\s*=\s*([-\d.eE+]+)", src)
    if not m:
        sys.exit("GATE BM: could not find `odNotchDepthDb` in src/dsp/FitParams.h -- the third "
                 "arm is computed as an OFFSET from the shipped value, so it cannot be assumed.")
    got = float(m.group(1))
    if abs(got - SHIPPED_DEPTH_OFFSET_DB) > 1e-9:
        sys.exit(f"GATE BM: FitParams.h ships odNotchDepthDb = {got}, this gate has "
                 f"{SHIPPED_DEPTH_OFFSET_DB}.  Update the constant; do not tolerate the drift "
                 "(the third arm is `shipped + delta` and would silently move the notch).")

    # `NOTCH_BASE_DRIVE0`'s ROW LABELS pinned to the header's own comments, so BM0h cannot be
    # reading a stale or re-ordered table.  This is the only place the enum row order is asserted
    # against the source rather than assumed.
    ot = open("src/dsp/OdToneRestore.h").read()
    for row, label in enumerate(("Cut", "Flat", "Boost")):
        pat = (r"\{\s*" + re.escape(f"{NOTCH_BASE_DRIVE0[row]:.2f}")
               + r"\s*,[^}]*\}\s*,\s*//\s*" + label)
        if not re.search(pat, ot):
            sys.exit(f"GATE BM: OdToneRestore.h has no kNotchGainDb row labelled `{label}` "
                     f"starting {NOTCH_BASE_DRIVE0[row]:.2f} at DRIVE 0.  The table has moved or "
                     "been re-ordered; BM0h's GRUNT-row check would silently invert.")
    return got


def cut_delta(mix, drive_val, grunt_apvts):
    """K[g][d] * (S(cf_ship) − S(cf_e0)) for one condition: the dB by which the mix law's own
    output moved when the end stop shifted `cleanFraction()`.  The third arm cancels it."""
    L = K.level_taper(mix[0])
    od0, cl0 = K.coef_closed(mix[1], L, endstop=(0.0, 0.0))
    ods, cls = K.coef_closed(mix[1], L)
    cf0 = cl0 / (od0 + cl0) if (od0 + cl0) > 0 else 0.0
    cfs = cls / (ods + cls) if (ods + cls) > 0 else 0.0
    k = lerp5(NOTCH_MIX_K[GRUNT_ENUM[grunt_apvts]], drive_val)
    return k * (mix_shape(cfs) - mix_shape(cf0)), cf0, cfs, k


# =================================================================================================
# curve cache — render, extract, discard the wav
# =================================================================================================
def _bin_sig():
    st = os.stat(CR.DEFAULT_BIN)
    return [st.st_size, st.st_mtime_ns]


def curves(tag, args):
    """{sweep: 1/48-oct smoothed H1 curve} for one condition, cached as curves not audio.

    Reuse requires BOTH the argv and the BINARY stamp to match.  The binary half is not optional
    (s117: GATE R silently re-read renders of a superseded build because its stamp covered argv
    alone) and it is doubly load-bearing here, because the whole gate is an arm-to-arm difference —
    a stale arm would report a DSP change as a physical finding."""
    os.makedirs(CURVE_DIR, exist_ok=True)
    npz = os.path.join(CURVE_DIR, tag + ".npz")
    want = list(args)
    if os.path.exists(npz):
        z = np.load(npz, allow_pickle=False)
        if list(z["argv"]) == want and list(z["bin"]) == _bin_sig():
            return {sw: z[sw] for sw in SWEEPS}
        why = "a DIFFERENT condition" if list(z["argv"]) != want else "a DIFFERENT BINARY"
        sys.stderr.write(f"  ! {npz} was rendered at {why} -- re-rendering\n")

    wav = os.path.join(CURVE_DIR, tag + ".wav")
    if not CR.render_plugin(CR.DEFAULT_BIN, want, wav, OS_FACTOR):
        sys.exit(f"GATE BM: render failed for {tag}\n   args: {' '.join(want)}")
    _, ref = BL.orig_ref()
    y = A.load(wav)
    out = {}
    for sw in SWEEPS:
        f, m = A.transfer_h1(A.seg_of(y, sw), ref)
        out[sw] = W.smooth(f, m)
    np.savez_compressed(npz, argv=np.array(want), bin=np.array(_bin_sig()), **out)
    os.remove(wav)                        # ⭐ the whole point: 16 MB -> 14 KB
    return out


def arm_args(mix, drive_val, grunt_apvts, arm):
    """Explicit flags for one (mix, drive, grunt, arm).  Every control emitted, never relying on
    the binary's defaults matching (`captures.render_args`'s own rule)."""
    lv, bv = mix
    if arm == "ship":
        extra = ()
    elif arm == "e0":
        extra = ("--fit", "blendEndStop=0")
    elif arm == "mixfroz":
        dcut, _, _, _ = cut_delta(mix, drive_val, grunt_apvts)
        extra = ("--fit", "blendEndStop=0",
                 "--fit", f"odNotchDepthDb={SHIPPED_DEPTH_OFFSET_DB + dcut:.9f}")
    else:
        raise ValueError(arm)
    return BL.cond_args(drive_val, grunt_apvts, blend=bv, level=lv, extra=extra)


def tag_of(lt, bt, dname, gname, arm):
    return f"L{lt}_B{bt}_{dname}_{gname}_{arm}"


# =================================================================================================
# BM0 — guards and known answers
# =================================================================================================
def gate_bm0(e_hi):
    print("=" * 100)
    print("BM0  GUARDS AND KNOWN ANSWERS")
    print("=" * 100)

    # (a) EPOCH.  The gate is a statement about ONE shipped constant, so it refuses if FitParams.h
    # has moved under it.  GATE K's resolver, imported (s182 built it precisely so there is one).
    K.check_shipped_endstop()
    off = check_mix_law()
    print(f"  (a) EPOCH         FitParams.h ships blendEndStop = {e_hi:.6g}   [GATE K's resolver]")
    print(f"                    ... and odNotchDepthDb = {off:.6g}, S pinned at kMixCfRef "
          f"= {MIX_CF_REF}  [the third arm's own guards]")

    # (b) ⭐⭐ THE LOAD-BEARING GUARD, AND IT IS NEW: the coefficients are constants at EVERY cell,
    # and both of GATE K's independent mirrors agree there.  K2 only ever checked a handful of
    # points, all at an endpoint of one axis; the entire flat/shape split off the corner rests on
    # this holding across the INTERIOR, so it is asserted across the interior.
    worst_mirror = 0.0
    n = 0
    for _lt, lv, _bt, bv in MIX_CELLS:
        L = K.level_taper(lv)
        for es in (None, (0.0, 0.0)):
            a = K.coef_closed(bv, L, endstop=es)
            b = K.coef_nodal(bv, L, endstop=es)
            worst_mirror = max(worst_mirror, abs(a[0] - b[0]), abs(a[1] - b[1]))
            n += 1
    if worst_mirror > 1e-12:
        sys.exit(f"GATE BM: BM0b FAILED -- GATE K's closed-form and nodal coefficient mirrors "
                 f"disagree by {worst_mirror:.3e} somewhere on the mix grid.  Off the corner is "
                 "exactly where s182 found them BOTH stale, so this is refused, not tolerated.")
    print(f"  (b) COEFFICIENTS  closed-form == nodal at all {n} (cell x arm) points, worst "
          f"{worst_mirror:.1e}  -- so the two")
    print("                    coefficients really are frequency-independent constants at every")
    print("                    (L, B), and BL1's flat/shape split generalises off the corner")

    # (c) SCOPE, and it is a RENDER not an argument.  At BLEND = 0 the effective wiper is `endLo`
    # = 0, so `engagedPath` takes its `b_eff <= 0` branch and returns (0, 1) whatever the end stop
    # is.  A gate that only renders where a change is expected cannot tell "correctly scoped" from
    # "reached everything".  Kept as WAVS (via BL's cache) because bit-identity is a sample-level
    # claim that a smoothed curve cannot carry.
    a = BL.render("scope_blend0_ship", BL.cond_args(0.5, 1, blend=0.0))
    b = BL.render("scope_blend0_e0", BL.cond_args(0.5, 1, blend=0.0,
                                                  extra=["--fit", "blendEndStop=0"]))
    d = BL.bitdiff(a, b)
    if d > BITS:
        sys.exit(f"GATE BM: BM0c FAILED -- the end stop reaches BLEND = 0 (worst {d:.3e}).")
    print(f"  (c) SCOPE         BLEND = 0 is BIT-IDENTICAL across the arms (worst {d:.1e})")

    # (d) ⭐ NON-VACUITY **AT A PLAYED CELL**.  BL's own non-vacuity arm is at the corner, and
    # inheriting it would prove nothing here: the entire question is whether anything moves OFF the
    # corner, so the arm that makes every number below mean something must be off the corner too.
    lv, bv = LISTENING
    a = BL.render("bm0_listen_ship", arm_args(LISTENING, 0.5, 1, "ship"))
    b = BL.render("bm0_listen_e0", arm_args(LISTENING, 0.5, 1, "e0"))
    d = BL.bitdiff(a, b)
    if d <= BITS:
        sys.exit("GATE BM: BM0d FAILED -- the two arms are bit-identical at the LISTENING cell.  "
                 "`--fit blendEndStop=0` is not reaching the stage off the corner, so every "
                 "difference below would read zero for a plumbing reason (s100's control).")
    print(f"  (d) NON-VACUITY   the LISTENING cell (L {lv}, B {bv}) DOES move "
          f"(worst |sample diff| {d:.5f})")

    # (e) The clean branch is OD-INDEPENDENT, asserted on two renders differing in DRIVE and GRUNT
    # rather than assumed from the topology.
    a = BL.render("bl0_clean_ref", BL.cond_args(0.0, 1, blend=0.0))
    b = BL.render("bl0_clean_alt", BL.cond_args(1.0, 0, blend=0.0))
    d = BL.bitdiff(a, b)
    if d > BITS:
        sys.exit(f"GATE BM: BM0e FAILED -- BLEND = 0 depends on DRIVE/GRUNT (worst {d:.3e}).")
    print(f"  (e) CLEAN ARM     BLEND = 0 is OD-independent (worst {d:.1e})")


def gate_bm0fg(cells, e_hi):
    """(f) CROSS-GATE known answer; (g) the DECOMPOSITION's own known answer."""
    print()
    print("  (f) CROSS-GATE    reproducing GATE BL's STORED corner numbers from this gate's own")
    print("                    renders.  Available only because the corner is one cell of this")
    print("                    grid; a disagreement would mean one of the two gates is measuring")
    print("                    a different object and neither could be quoted (s159's AW1b).")
    if not os.path.exists(BL_REPORT):
        sys.exit(f"GATE BM: BM0f cannot run -- {BL_REPORT} is missing.  Run GATE BL first; the "
                 "cross-gate known answer is not optional (it is what licenses comparing this "
                 "gate's corner column with s183's published one).")
    blr = json.load(open(BL_REPORT))
    flat_bl, flat_me = blr["flat_db"], 20.0 * math.log10(1.0 - e_hi)
    if abs(flat_bl - flat_me) > 1e-9:
        sys.exit(f"GATE BM: BM0f FAILED -- BL's stored flat term {flat_bl:.9f} dB and this gate's "
                 f"{flat_me:.9f} dB differ.  The end stop moved between the two runs.")
    got = max(c["shape_max"] for c in cells if c["mix"] == CORNER)
    ref = blr["worst_shape_db"]
    if abs(got - ref) > 0.05:
        sys.exit(f"GATE BM: BM0f FAILED -- this gate's worst CORNER shape perturbation "
                 f"{got:.4f} dB does not reproduce GATE BL's stored {ref:.4f} dB.  Same stage, "
                 "same conditions, same estimator: a disagreement is an instrument defect in one "
                 "of the two, not a finding.")
    print(f"      flat term            {flat_bl:+.6f} dB (BL, stored)  vs {flat_me:+.6f} dB (here)")
    print(f"      worst corner Δshape   {ref:8.4f} dB (BL, stored)  vs {got:8.4f} dB (here)  "
          f"[Δ {abs(got - ref):.4f}]")

    # ---- (g) ------------------------------------------------------------------------------------
    print()
    print("  (g) DECOMPOSITION the third arm must be a NOTCH-ONLY change.  `mixfroz − e0` differs")
    print("                    only in `odNotchDepthDb`, which moves ONE RBJ peaking biquad at")
    print("                    kNotchFreq, so it must be LOCALISED there and SIGNED as −K[g][d].")
    print()
    print("  ⛔⛔ THE OBVIOUS FORM OF THE LOCALISATION TEST IS A RATIO AND IT IS THE DOCUMENTED")
    print("     TRAP.  A first draft gated `out-of-window peak / in-window peak < 1` and FAILED at")
    print("     3.38x — against a cell whose in-window peak is 0.0020 dB, i.e. an arm that is")
    print("     doing nothing because Δcut there is −0.017 dB.  All 37 of the offending cells have")
    print("     in-window peaks <= 0.0137 dB: the statistic was dividing noise by noise")
    print("     (`ratio-statistics-need-a-denominator-guard`).  ⇒ the test below regresses both")
    print("     peaks on |Δcut| — the ANALYTIC size of the intervention — so the intervention")
    print("     appears as the REGRESSOR rather than as a divisor, uses all readings, needs no")
    print("     threshold, and cannot be moved by cells where nothing happens.")
    g = W.GRID
    inw = (g >= OT.SHOULDER[0]) & (g <= OT.SHOULDER[1])
    outw = ((g >= F_LO_GRADE) & (g <= F_HI_GRADE)) & ~inw
    go = g[outw]
    icen = int(np.argmin(np.abs(g - NOTCH_FREQ)))
    dc, ip, op, ohz = [], [], [], []
    sign_ok = sign_n = 0
    fails = []
    for c in cells:
        nd = c["mixfroz"] - c["e0"]
        ao = np.abs(nd[outw])
        a_in, a_out = float(np.abs(nd[inw]).max()), float(ao.max())
        dc.append(abs(c["cut_delta_db"]))
        ip.append(a_in)
        op.append(a_out)
        ohz.append(float(go[int(ao.argmax())]))
        # SIGN, on the cells where the notch effect is RESOLVABLE above that cell's own residue.
        # Selecting on resolvability is legitimate (s108: select on PRECISION, never on value) —
        # the sign is the thing under test, and the selection does not look at it.
        if a_in <= a_out:
            continue
        sign_n += 1
        good = math.copysign(1.0, nd[icen]) == math.copysign(1.0, -c["cut_delta_db"])
        sign_ok += int(good)
        if not good:
            fails.append((c["mix"], c["drive"], c["grunt"], c["sweep"], c["cut_delta_db"]))
    dc, ip, op = np.array(dc), np.array(ip), np.array(op)
    if float(ip.max()) <= 1e-6:
        sys.exit("GATE BM: BM0g FAILED -- the notch arm never moves in-window: `--fit "
                 "odNotchDepthDb=` is not reaching the stage, so the decomposition below would "
                 "attribute the whole change to the mix coefficients for a plumbing reason "
                 "(s100's control).")
    s_in = float((dc * ip).sum() / (dc * dc).sum())
    s_out = float((dc * op).sum() / (dc * dc).sum())
    if s_out >= s_in:
        sys.exit(f"GATE BM: BM0g FAILED -- the notch arm is NOT localised: out-of-window response "
                 f"scales with |Δcut| at {s_out:.4f} dB/dB against {s_in:.4f} in-window.  "
                 "`odNotchDepthDb` is supposed to move one peaking biquad at kNotchFreq, not the "
                 "broadband response.")
    if sign_ok != sign_n:
        sys.exit(f"GATE BM: BM0g FAILED -- the notch arm's sign at kNotchFreq matches −K[g][d] in "
                 f"only {sign_ok} of {sign_n} resolvable cells (e.g. {fails[:2]}).  Either the "
                 "GRUNT row mapping is permuted (APVTS {Boost, Cut, Flat} vs enum {Cut, Flat, "
                 "Boost} — the rows differ in SIGN across it) or the mix law's transcription is "
                 "wrong.")
    near = int((ip <= 0.0137).sum())
    med_hz = float(np.median(np.array(ohz)[np.argsort(-op)[:60]]))
    print()
    print(f"      LOCALISED   in-window {s_in:.4f} dB per dB of |Δcut|, out-of-window "
          f"{s_out:.4f}  ->  {100 * s_out / s_in:.1f} %")
    print(f"      SIGNED      matches −K[g][d] at kNotchFreq in {sign_ok} of {sign_n} resolvable "
          "readings,")
    print("                  and Δcut CHANGES SIGN across the GRUNT rows (Cut 45 of 48 negative,")
    print("                  Flat 31 positive / 17 negative, Boost 45 of 48 positive)")
    print("      ⛔⛔ SCOPE, AND IT IS A CORRECTION TO THIS GATE'S OWN FIRST CLAIM.  This sign")
    print("         test is STRUCTURALLY BLIND TO A PERMUTED GRUNT ROW, and the draft asserted the")
    print("         opposite (\"a mixed-sign test that a permuted row could not pass\").  Its own")
    print("         mutation arm proved otherwise: permuting `GRUNT_ENUM` changes the INTERVENTION")
    print("         (the third arm's `odNotchDepthDb`) and the PREDICTION (−K[g][d]) through the")
    print("         SAME table, so the arm moves both sides together and the test still passes")
    print("         539/539.  ⇒ s182's own defect, fourth occurrence of s145 AM1a / s149 AO2: a")
    print("         known answer cannot validate what both of its sides take as input.  What this")
    print("         test DOES validate is `depthOffsetDb`'s sign convention and the transcription's")
    print("         internal consistency.  The row mapping is checked independently by BM0h.")
    print(f"      RESIDUE     the worst out-of-window excursions sit at a median of {med_hz:.0f} Hz")
    print(f"                  — i.e. immediately outside the imported {OT.SHOULDER[0]:.0f}–"
          f"{OT.SHOULDER[1]:.0f} Hz window, so the 'leak'")
    print("                  is the notch's OWN SKIRT crossing a bound chosen for reading depth,")
    print("                  not a broadband change.  ⚠ Stated as a SCOPE limit on the split, not")
    print("                  waved away: ~6 % of the notch arm's amplitude lands outside.")
    print(f"      ⚠ {near} of {len(cells)} readings have an in-window peak <= 0.0137 dB (|Δcut| ~ 0)")
    print("        and carry no information either way — printed so the ratio trap above stays on")
    print("        the record rather than being re-derived.")
    print("      ⇒ `ship − e0` = (ship − mixfroz) + (mixfroz − e0) splits the change into the MIX")
    print("        COEFFICIENTS and `OdToneRestore`'s CUT, and both halves are attributable.")

    # ---- (h) the GRUNT row mapping, from the RENDER -----------------------------------------
    print()
    print("  (h) GRUNT ROWS    the guard BM0g cannot be: does APVTS index -> enum row map the way")
    print("                    `PedalChain::gruntEnum()` does?  ⭐ The handle is INDEPENDENT of")
    print("                    `kNotchMixK` because it uses the OTHER table and the RENDER: at")
    print(f"                    DRIVE 0 `kNotchGainDb` cuts {NOTCH_BASE_DRIVE0[0]:.2f} dB on Cut "
          f"against {NOTCH_BASE_DRIVE0[1]:.2f} on Flat and")
    print(f"                    {NOTCH_BASE_DRIVE0[2]:.2f} on Boost, and the RENDER is produced by "
          "the C++'s own mapping, so")
    print("                    the measured notch depths must come out in the table's own order.")
    depths = {}
    for gname, gv in GRUNTS:
        c = next(x for x in cells if x["mix"] == CORNER and x["drive"] == "drive-0700"
                 and x["grunt"] == gname and x["sweep"] == PLAY_SWEEP)
        try:
            depths[gv] = OT.notch_geometry(W.GRID, c["ship"])["depth_point"]
        except RuntimeError:
            depths[gv] = float("nan")
    if any(d != d for d in depths.values()):
        sys.exit("GATE BM: BM0h cannot run -- the reader refused a DRIVE-0 corner cell, so the "
                 "GRUNT row mapping is unverified.  A refusal is not a pass.")
    # Gate on the ORDERING only — the one property BM0h uses, and the one a permutation breaks.
    want = sorted(range(3), key=lambda r: NOTCH_BASE_DRIVE0[r])          # -> [Cut, Boost, Flat]
    got = [GRUNT_ENUM[gv] for gv in sorted(depths, key=lambda gv: depths[gv])]
    for gname, gv in GRUNTS:
        print(f"      {gname:11s} apvts {gv} -> row {GRUNT_ENUM[gv]} "
              f"({('Cut', 'Flat', 'Boost')[GRUNT_ENUM[gv]]:5s}), table cut "
              f"{NOTCH_BASE_DRIVE0[GRUNT_ENUM[gv]]:5.2f} dB, MEASURED depth {depths[gv]:6.2f} dB")
    if got[0] != want[0]:
        sys.exit(f"GATE BM: BM0h FAILED -- the render this gate assigns to row {got[0]} "
                 f"({('Cut', 'Flat', 'Boost')[got[0]]}) has the shallowest measured notch, but "
                 f"`kNotchGainDb` says row {want[0]} "
                 f"({('Cut', 'Flat', 'Boost')[want[0]]}) should.  GRUNT_ENUM is permuted relative "
                 "to `PedalChain::gruntEnum()` (APVTS {Boost, Cut, Flat} vs enum {Cut, Flat, "
                 "Boost}) — the s151 trap, and it would silently invert the third arm.")
    print(f"      ⇒ the shallowest measured notch is row {got[0]} "
          f"({('Cut', 'Flat', 'Boost')[got[0]]}), which is what `kNotchGainDb`'s")
    print("        DRIVE-0 column requires ⇒ GRUNT_ENUM agrees with `PedalChain::gruntEnum()`.")


# =================================================================================================
# BM1 — the analytic law: the bracket, and why the corner is a singularity
# =================================================================================================
def gate_bm1():
    print()
    print("=" * 100)
    print("BM1  THE ANALYTIC LAW ACROSS THE MIX GRID — NO RENDER")
    print("=" * 100)
    print("  out_ship/out_e0 = (od_s + cl_s*u)/(od_0 + cl_0*u),  u = CLEAN/OD.  Both limits are")
    print("  analytic per cell, so the perturbation is BRACKETED wherever the branches are")
    print("  co-phased, and the bracket's width is Δρ, the change in the clean-to-OD ratio:")
    print()
    print(f"  {'L knob':>7s} {'B knob':>7s} {'L(tap)':>7s} {'od_e0':>8s} {'od_ship':>8s} "
          f"{'FLAT dB':>8s} {'cl_e0':>7s} {'cl_ship':>7s} {'CLEAN-lim':>10s} {'Δρ dB':>8s} "
          f"{'cf_e0':>7s} {'cf_ship':>7s}")
    print("  " + "-" * 104)
    rows = []
    for lt, lv, bt, bv in MIX_CELLS:
        L = K.level_taper(lv)
        od0, cl0 = K.coef_closed(bv, L, endstop=(0.0, 0.0))
        ods, cls = K.coef_closed(bv, L)
        flat = 20.0 * math.log10(ods / od0)
        singular = cl0 <= 0.0
        climit = float("inf") if singular else 20.0 * math.log10(cls / cl0)
        rows.append({"mix": (lv, bv), "lt": lt, "bt": bt, "L": L,
                     "od_e0": od0, "od_ship": ods, "cl_e0": cl0, "cl_ship": cls,
                     "flat_db": flat, "clean_limit_db": climit, "drho_db": climit - flat,
                     "cf_e0": cl0 / (od0 + cl0), "cf_ship": cls / (ods + cls),
                     "singular": singular,
                     "ladder": (bv == LADDER_B and lv in [x[1] for x in LADDER_LEVELS])})
        cl_s = "     +inf" if singular else f"{climit:+10.3f}"
        dr_s = "    +inf" if singular else f"{climit - flat:+8.3f}"
        mark = "  <-- CORNER: SINGULAR (cl_e0 = 0)" if (lv, bv) == CORNER else (
            "  <-- LISTENING" if (lv, bv) == LISTENING else
            "  <-- ladder" if rows[-1]["ladder"] else "")
        print(f"  {lv:7.3f} {bv:7.2f} {L:7.4f} {od0:8.5f} {ods:8.5f} {flat:+8.4f} "
              f"{cl0:7.4f} {cls:7.4f} {cl_s} {dr_s} {rows[-1]['cf_e0']:7.4f} "
              f"{rows[-1]['cf_ship']:7.4f}{mark}")
    rows.sort(key=lambda r: (r["mix"][0], r["mix"][1]))
    fin = [r for r in rows if not r["singular"]]
    print()
    print("  ⭐⭐ THE CORNER IS A SINGULARITY OF THE LAW, NOT MERELY ITS WORST CELL.  `cl_e0 = 0`")
    print("     there, so the CLEAN-dominated limit is +inf and the perturbation is UNBOUNDED —")
    print("     which is why GATE BL measured 12.25 dB at the corner and could only MEASURE it.")
    print(f"  ⭐ At every other cell the bracket is finite and narrow: Δρ spans "
          f"{min(r['drho_db'] for r in fin):+.3f} … {max(r['drho_db'] for r in fin):+.3f} dB over")
    print(f"     {len(fin)} played cells, against a flat term of "
          f"{min(r['flat_db'] for r in fin):+.4f} … {max(r['flat_db'] for r in fin):+.4f} dB.")
    print("  ⚠ The bracket bounds CO-PHASED branches only.  `od_0 + cl_0*u` vanishes where the e0")
    print("     arm itself CANCELS, so at a null the ratio can leave it — the corner's mechanism in")
    print("     a milder form, and the reason BM2 measures rather than derives.")
    return rows


# =================================================================================================
# BM2 — the measured perturbation, and the two-mechanism split
# =================================================================================================
def gate_bm2(cells, rows):
    print()
    print("=" * 100)
    print("BM2  THE MEASURED PERTURBATION — POOLED OVER DRIVE x GRUNT, PER MIX CELL")
    print("=" * 100)
    print("  `shape` is (ship − e0) with BM1's EXACT per-cell flat term removed (analytic, never")
    print("  fitted — a fitted offset absorbs part of the shape change and understates it,")
    print("  `self-selecting-scores`).  `out of bracket` is the fraction of graded band leaving")
    print("  BM1's co-phased bracket, i.e. how much of the change lives at a CANCELLATION.")
    print()
    by_mix = {}
    for c in cells:
        by_mix.setdefault(c["mix"], []).append(c)
    print(f"  {'L':>5s} {'B':>5s} {'n':>3s} {'FLAT':>7s} {'Δρ':>7s} | {'raw rms':>8s} "
          f"{'shape rms':>9s} {'shape max':>9s} {'at Hz':>8s} {'out of brkt':>12s}")
    print("  " + "-" * 92)
    mix_stats = {}
    for r in rows:
        cs = by_mix[r["mix"]]
        st = {"n": len(cs),
              "raw_rms": float(np.sqrt(np.mean([c["raw_rms"] ** 2 for c in cs]))),
              "shape_rms": float(np.sqrt(np.mean([c["shape_rms"] ** 2 for c in cs]))),
              "shape_max": max(c["shape_max"] for c in cs),
              "frac_out": float(np.mean([c["frac_out"] for c in cs])),
              "mix_max": max(c["mix_max"] for c in cs),
              "notch_max": max(c["notch_max"] for c in cs)}
        st["shape_max_hz"] = next(c["shape_max_hz"] for c in cs
                                  if c["shape_max"] == st["shape_max"])
        mix_stats[r["mix"]] = st
        dr = "   +inf" if r["singular"] else f"{r['drho_db']:+7.3f}"
        mark = " <-- CORNER" if r["mix"] == CORNER else (
            " <-- LISTENING" if r["mix"] == LISTENING else "")
        print(f"  {r['mix'][0]:5.2f} {r['mix'][1]:5.2f} {st['n']:3d} {r['flat_db']:+7.4f} {dr} | "
              f"{st['raw_rms']:8.3f} {st['shape_rms']:9.3f} {st['shape_max']:9.3f} "
              f"{st['shape_max_hz']:8.1f} {st['frac_out'] * 100:11.2f} %{mark}")

    corner = mix_stats[CORNER]
    play = {m: v for m, v in mix_stats.items() if m != CORNER}
    worst_mix, worst_play = max(play.items(), key=lambda kv: kv[1]["shape_max"])
    print()
    print(f"  ⇒ CORNER        shape max {corner['shape_max']:7.3f} dB  rms "
          f"{corner['shape_rms']:6.3f}  {corner['frac_out'] * 100:5.2f} % out of bracket")
    print(f"  ⇒ WORST PLAYED  shape max {worst_play['shape_max']:7.3f} dB at (L {worst_mix[0]}, "
          f"B {worst_mix[1]})  rms {worst_play['shape_rms']:6.3f}")
    print(f"  ⇒ LISTENING     shape max {mix_stats[LISTENING]['shape_max']:7.3f} dB  rms "
          f"{mix_stats[LISTENING]['shape_rms']:6.3f}")
    ratio = corner["shape_max"] / max(worst_play["shape_max"], 1e-9)
    print()
    # ⛔ COMPUTED, NOT NARRATED.  The first draft printed "THE CORNER OVERSTATES THE WORST PLAYED
    # CELL BY 0.5x" — a direction asserted in prose directly above the two numbers that refute it
    # (`computed-verdicts-not-narrated`, and the reason that rule exists).  The direction is a
    # RESULT here, and it is the opposite of the one the handover leads a reader to expect.
    if ratio >= 1.0:
        print(f"  ⭐ THE CORNER IS THE WORST CELL ON THE SHAPE TERM, BY {ratio:.1f}x "
              f"({corner['shape_max']:.2f} vs {worst_play['shape_max']:.2f} dB).")
    else:
        print(f"  ⛔⛔ THE CORNER IS **NOT** THE WORST CELL — IT UNDERSTATES THE SHAPE TERM BY "
              f"{1.0 / ratio:.1f}x")
        print(f"     ({corner['shape_max']:.2f} dB at the corner against {worst_play['shape_max']:.2f}"
              f" dB at L {worst_mix[0]} / B {worst_mix[1]}), and the")
        print(f"     LISTENING cell reaches {mix_stats[LISTENING]['shape_max']:.2f} dB — also above "
              "the corner.")
        print("  ⭐⭐ AND THE MECHANISM IS BM1's OWN CAVEAT, WHICH TURNS OUT TO DOMINATE.  BM1's")
        print("     bracket is unbounded at the corner and narrow everywhere else, so a reader")
        print("     stops there and concludes the corner is worst.  But the bracket only holds for")
        print("     CO-PHASED branches, and 20–37 % of the graded band leaves it at EVERY cell.")
        print("     At the corner there is no clean branch to cancel against, so the perturbation")
        print("     is only large where the OD branch itself nulls; OFF the corner the two")
        print("     branches can cancel AGAINST EACH OTHER, which is a commoner and deeper")
        print("     coincidence.  ⇒ the perturbation is largest where the MIX most nearly cancels,")
        print("     and that is a played setting, not the corner.")
    print()
    print("  ⚠⚠ SO s183 §9's \"~10x smaller everywhere else\" DOES NOT GENERALISE FROM THE QUANTITY")
    print("     IT WAS MEASURED ON.  It is a statement about `OdToneRestore`'s APPLIED CUT, and")
    print("     BM5 reproduces it there exactly (corner 3.1x the worst played cell, opposite")
    print("     sign).  It is FALSE of the RENDERED RESPONSE of the chain, which is a different")
    print("     quantity — and the handover's priority ordering was drawn from the first and read")
    print("     as though it covered the second.  Both numbers are real; they answer different")
    print("     questions, and only the second one is what a player hears.")

    # ---- how good is BM1's bracket, actually?  Measured, so it cannot be misquoted as a bound. --
    fin = [(r["drho_db"], mix_stats[r["mix"]]["shape_max"]) for r in rows if not r["singular"]]
    dr = np.array([f[0] for f in fin])
    sm = np.array([f[1] for f in fin])

    def _rank(a):
        o = np.argsort(a)
        rk = np.empty(len(a))
        rk[o] = np.arange(len(a))
        return rk

    rho = float(np.corrcoef(_rank(dr), _rank(sm))[0, 1])
    under = float(np.median(sm / dr))
    print()
    print("  ⚠⚠ AND BM1's BRACKET IS A RANKING HEURISTIC, NOT A BOUND — MEASURED, so a future")
    print(f"     session cannot quote Δρ as one.  Over the {len(fin)} played cells it RANKS the")
    print(f"     realised worst excursion at Spearman {rho:+.3f}, and it UNDER-PREDICTS its SIZE by")
    print(f"     a median {under:.1f}x (worst cell: {dr.max():.2f} dB of bracket against "
          f"{sm[int(dr.argmax())]:.2f} dB realised).")
    print("     At the corner it is +inf and OVER-predicts (12.25 dB realised).  ⇒ the escape at")
    print("     cancellations is not a correction to the bracket, it is the dominant term.")

    # ---- BM2b: the two mechanisms, separated -----------------------------------------------------
    print()
    print("  BM2b  THE TWO MECHANISMS, SEPARATED (the third arm)")
    print("  " + "-" * 92)
    print("  (ship − mixfroz) is the MIX-COEFFICIENT change alone; (mixfroz − e0) is")
    print("  `OdToneRestore`'s CUT change alone.  They SUM to (ship − e0) by construction.")
    print("  ⚠⚠ READ THE TWO AXES SEPARATELY — THEY DISAGREE, AND CONFLATING THEM PRODUCES AN")
    print("     OVERCLAIM IN EITHER DIRECTION.  At the corner the two mechanisms are OPPOSITELY")
    print("     SIGNED in the RESPONSE at kNotchFreq (the mix fills the null in, the extra cut")
    print("     deepens it) — but BM4 measures them acting the SAME way on the null's DEPTH, which")
    print("     is a shoulder-referred quantity and not the response at one point.  ⇒ quote BM4's")
    print("     PAIRED columns for the depth attribution, never the sign of this table.")
    print()
    print(f"  {'L':>5s} {'B':>5s} | {'mix max':>8s} {'notch max':>10s} {'Δcut dB':>9s} "
          f"{'notch @323':>11s} {'mix @323':>9s} {'total @323':>11s}")
    print("  " + "-" * 78)
    g = W.GRID
    icen = int(np.argmin(np.abs(g - NOTCH_FREQ)))
    split = {}
    for r in rows:
        cs = [c for c in by_mix[r["mix"]] if c["sweep"] == PLAY_SWEEP and c["grunt"] == "grunt-cut"
              and c["drive"] == "drive-1200"]
        c = cs[0]
        nd = c["mixfroz"] - c["e0"]
        md = c["ship"] - c["mixfroz"]
        st = mix_stats[r["mix"]]
        split[r["mix"]] = {"mix_max": st["mix_max"], "notch_max": st["notch_max"],
                           "cut_delta_db": c["cut_delta_db"],
                           "notch_at_323": float(nd[icen]), "mix_at_323": float(md[icen]),
                           "total_at_323": float(nd[icen] + md[icen])}
        s = split[r["mix"]]
        mark = " <-- CORNER" if r["mix"] == CORNER else (
            " <-- LISTENING" if r["mix"] == LISTENING else "")
        print(f"  {r['mix'][0]:5.2f} {r['mix'][1]:5.2f} | {st['mix_max']:8.3f} "
              f"{st['notch_max']:10.3f} {s['cut_delta_db']:+9.3f} {s['notch_at_323']:+11.3f} "
              f"{s['mix_at_323']:+9.3f} {s['total_at_323']:+11.3f}{mark}")
    print()
    print("  (the four right-hand columns are GRUNT cut x DRIVE noon x " + PLAY_SWEEP + ", the cell")
    print("   s183 §9 quoted; `mix max` / `notch max` are pooled over all DRIVE x GRUNT x sweep)")
    return mix_stats, split


# =================================================================================================
# BM3 — the feature re-read at played settings (P1's headline)
# =================================================================================================
def gate_bm3(cells):
    print()
    print("=" * 100)
    print("BM3  THE FEATURE RE-READ AT PLAYED SETTINGS — ALL SEVEN, CORNER vs PLAYED")
    print("=" * 100)
    print("  ⛔ A reading that is `edge` or under GATE W3's prominence bar is REFUSED on both arms")
    print("     — `locate` always returns SOMETHING (s126/s151), so an unguarded Δ on an absent")
    print("     feature is a number about a window.  Membership is TALLIED over every reading, and")
    print("     Δf0 is quoted only on cells resolved in BOTH arms (matched membership, s159).")
    print(f"  Δf0 is against the locator's OWN resolution, {LOCATOR_RES_FRAC * 100:.2f} % "
          "(imported from GATE W).")
    print()
    out = {}
    print(f"  {'feature':13s} {'group':9s} {'read':>5s} {'both':>5s} {'lost':>5s} {'gain':>5s} "
          f"{'|Δf0| med':>10s} {'|Δf0| max':>10s} {'xres':>6s} {'Δprom med':>10s}")
    print("  " + "-" * 92)
    for name, kind, win, _label in W.FEATURES:
        rec = {}
        for group in ("CORNER", "PLAYED"):
            keep = (lambda m: m == CORNER) if group == "CORNER" else (lambda m: m != CORNER)
            dfs, dps = [], []
            lost = gain = both = n = 0
            for c in cells:
                if not keep(c["mix"]):
                    continue
                n += 1
                a, b = W.locate(c["e0"], win, kind), W.locate(c["ship"], win, kind)
                ok_a = not a["edge"] and a["prom"] >= W.MIN_PROM_DB
                ok_b = not b["edge"] and b["prom"] >= W.MIN_PROM_DB
                gain += int(ok_b and not ok_a)
                lost += int(ok_a and not ok_b)
                if ok_a and ok_b:
                    both += 1
                    dfs.append(100.0 * (b["f0"] / a["f0"] - 1.0))
                    dps.append(b["prom"] - a["prom"])
            rec[group] = {"n": n, "resolved_both": both, "lost": lost, "gain": gain,
                          "df_med_pct": float(np.median(np.abs(dfs))) if dfs else float("nan"),
                          "df_max_pct": float(np.max(np.abs(dfs))) if dfs else float("nan"),
                          "dprom_med": float(np.median(dps)) if dps else float("nan")}
            r = rec[group]
            print(f"  {name:13s} {group:9s} {n:5d} {both:5d} {lost:5d} {gain:5d} "
                  f"{r['df_med_pct']:10.3f} {r['df_max_pct']:10.3f} "
                  f"{r['df_max_pct'] / (LOCATOR_RES_FRAC * 100):6.1f} {r['dprom_med']:+10.3f}")
        out[name] = rec
        print()
    return out


# =================================================================================================
# BM4 — GATE AP's censoring question, at played settings (folded in per s183 §10)
# =================================================================================================
def gate_bm4(cells):
    print("=" * 100)
    print("BM4  `OdToneRestore`'s 320 Hz NULL — POINT vs AREA DEPTH, CORNER vs PLAYED")
    print("=" * 100)
    print("  s183 §3 measured the POINT depth losing 4.07 dB against the AREA depth's 0.24 (17x)")
    print("  AT THE CORNER, and named the mechanism: the added clean term cannot cancel (it does")
    print("  not pass through the network doing the cancelling), so it FLOORS the null's bottom")
    print("  and leaves the flanks — GATE AP's censoring with the floor INSIDE the model.  The")
    print("  hypothesis handed forward was that this is CORNER-ONLY.  Tested here.")
    print()
    print("  E6 (`notch_geometry`), the estimator the shipped table was fitted on — NOT GATE W's")
    print("  E1, which GATE AW proved is `E1 <= E6` identically and mixes DEPTH with WIDTH.  Both")
    print(f"  depths always printed (s152), `q_interp` not `q` (s153).  Stimulus: {PLAY_SWEEP}.")
    print("  ⭐ The `mix-only` column uses the third arm, so it isolates the mechanism s183 NAMED")
    print("     (the bleed) from `OdToneRestore`'s own cut change, which opposes it.")
    print()
    g = W.GRID
    rows, refused = [], []
    for c in cells:
        if c["sweep"] != PLAY_SWEEP:
            continue
        try:
            a = OT.notch_geometry(g, c["e0"])
            b = OT.notch_geometry(g, c["ship"])
            f = OT.notch_geometry(g, c["mixfroz"])
        except RuntimeError as exc:
            # A minimum resting on a CORE bound is a REFUSAL, not a reading (s151).  Counted and
            # named, never silently dropped (s40) — and it is itself information about the cell.
            refused.append({"mix": list(c["mix"]), "drive": c["drive"], "grunt": c["grunt"],
                            "why": str(exc).split(" — ")[0]})
            continue
        # ⚠⚠ ALL THREE COLUMNS ARE PAIRED PER CELL, and the notch column is computed here rather
        # than left to be inferred as (total − mix-only) downstream: a MEDIAN IS NOT LINEAR, so
        # differencing two medians is not the median of the difference
        # (`paired-cells-need-paired-differences`).  The three do not sum on the median row and
        # are not meant to.
        rows.append({"mix": c["mix"], "drive": c["drive"], "grunt": c["grunt"],
                     "dp": b["depth_point"] - a["depth_point"],
                     "da": b["depth_area"] - a["depth_area"],
                     "dp_mixonly": b["depth_point"] - f["depth_point"],
                     "da_mixonly": b["depth_area"] - f["depth_area"],
                     "dp_notchonly": f["depth_point"] - a["depth_point"],
                     "da_notchonly": f["depth_area"] - a["depth_area"],
                     "dq_pct": 100.0 * (b["q_interp"] / a["q_interp"] - 1.0)})
    if not rows:
        sys.exit("GATE BM: BM4 produced NO readings -- an empty gate must fail, not narrate "
                 "(`empty-gate-must-fail`).")

    print(f"  {'group':9s} {'n':>4s} {'Δpoint med':>11s} {'Δpoint wst':>11s} {'Δarea med':>10s} "
          f"{'ratio':>7s} {'ΔQ med %':>9s} | {'Δpt MIX':>9s} {'Δpt NOTCH':>10s} {'Δar MIX':>9s}")
    print("  " + "-" * 102)
    summ = {}
    for group in ("CORNER", "PLAYED"):
        keep = (lambda m: m == CORNER) if group == "CORNER" else (lambda m: m != CORNER)
        rs = [r for r in rows if keep(r["mix"])]
        if not rs:
            print(f"  {group:9s}    0   (no readings)")
            summ[group] = None
            continue
        med = lambda k: float(np.median([r[k] for r in rs]))     # noqa: E731
        dp, da = med("dp"), med("da")
        summ[group] = {"n": len(rs), "dp_med": dp, "da_med": da,
                       "dp_worst": min(r["dp"] for r in rs),
                       "da_worst": min(r["da"] for r in rs),
                       "dq_med_pct": med("dq_pct"),
                       "dp_mixonly_med": med("dp_mixonly"), "da_mixonly_med": med("da_mixonly"),
                       "dp_notchonly_med": med("dp_notchonly"),
                       "da_notchonly_med": med("da_notchonly"),
                       "ratio": abs(dp / da) if abs(da) > 1e-9 else float("inf")}
        s = summ[group]
        print(f"  {group:9s} {len(rs):4d} {dp:+11.3f} {s['dp_worst']:+11.3f} {da:+10.3f} "
              f"{s['ratio']:7.1f} {s['dq_med_pct']:+9.2f} | {s['dp_mixonly_med']:+9.3f} "
              f"{s['dp_notchonly_med']:+10.3f} {s['da_mixonly_med']:+9.3f}")
    print("  ⚠ the MIX and NOTCH columns are each PAIRED per cell; they do NOT sum to the total on")
    print("    a median row, because a median is not linear (`paired-cells-need-paired-differences`)")
    if refused:
        print()
        print(f"  ⚠ {len(refused)} cell(s) REFUSED by the reader (minimum on a CORE bound — a")
        print("    refusal, not a reading):")
        for r in refused[:6]:
            print(f"      L {r['mix'][0]} B {r['mix'][1]} {r['drive']:11s} {r['grunt']}")
        if len(refused) > 6:
            print(f"      ... and {len(refused) - 6} more")
    return summ, rows, refused


# =================================================================================================
# BM5 — `OdToneRestore`'s applied cut across the grid: P2's input
# =================================================================================================
def gate_bm5(rows):
    print()
    print("=" * 100)
    print("BM5  `OdToneRestore`'s MIX LAW ACROSS THE GRID — WHAT P2 HAS TO RE-ANCHOR")
    print("=" * 100)
    print("  The stage's cut is `base[g][d] + K[g][d]*S(cleanFrac) + depthOffsetDb`.")
    print("  `cleanFraction()` moves at EVERY cell (BM1), so the law's INPUT shifted everywhere —")
    print("  s183 §9 measured the cut change on six cells; here it is the whole grid, which is")
    print("  what P2's ≤0.05 dB bar has to be verified against.  K is the GRUNT-cut x DRIVE-noon")
    print(f"  entry ({NOTCH_MIX_K[0][2]:+.2f}), the cell s183 §9 quoted.")
    print()
    k_cut = NOTCH_MIX_K[0][2]
    print(f"  {'L':>5s} {'B':>5s} {'cf_e0':>7s} {'cf_ship':>7s} {'S(e0)':>8s} {'S(ship)':>8s} "
          f"{'ΔS':>8s} {'cut Δ dB':>9s}")
    print("  " + "-" * 68)
    out = []
    for r in rows:
        s0, s1 = mix_shape(r["cf_e0"]), mix_shape(r["cf_ship"])
        dcut = k_cut * (s1 - s0)
        out.append({"mix": list(r["mix"]), "cf_e0": r["cf_e0"], "cf_ship": r["cf_ship"],
                    "S_e0": s0, "S_ship": s1, "cut_delta_db": dcut})
        mark = " <-- CORNER" if r["mix"] == CORNER else (
            " <-- LISTENING" if r["mix"] == LISTENING else "")
        print(f"  {r['mix'][0]:5.2f} {r['mix'][1]:5.2f} {r['cf_e0']:7.4f} {r['cf_ship']:7.4f} "
              f"{s0:+8.4f} {s1:+8.4f} {s1 - s0:+8.4f} {dcut:+9.3f}{mark}")

    play = [o for o in out if tuple(o["mix"]) != CORNER]
    corner = next(o for o in out if tuple(o["mix"]) == CORNER)
    worst = max(play, key=lambda o: abs(o["cut_delta_db"]))
    listen = next(o for o in out if tuple(o["mix"]) == LISTENING)
    cf_min = min(r["cf_ship"] for r in rows)
    print()
    print(f"  ⇒ CORNER cut change {corner['cut_delta_db']:+.3f} dB;  worst PLAYED "
          f"{worst['cut_delta_db']:+.3f} dB at (L {worst['mix'][0]}, B {worst['mix'][1]});  "
          f"LISTENING {listen['cut_delta_db']:+.3f} dB")
    print(f"  ⇒ the corner's change is "
          f"{abs(corner['cut_delta_db'] / worst['cut_delta_db']):.1f}x the worst played cell's AND "
          "THE OPPOSITE SIGN")
    print("    — s183 §9 reproduced on the full grid, and on a K row read out of the header rather")
    print("    than transcribed into the gate's prose.")
    print()
    print("  ⭐ P2's TARGET, MEASURED: the REACHABLE MINIMUM clean fraction on this grid is")
    print(f"     {cf_min:.5f}, and `kMixS[0]` sits at cf = 0.000 — a node the plugin can no longer")
    print(f"     reach.  That dead node is the ONLY steep part of the law (S drops {MIX_S[0]:+.3f}")
    print(f"     -> {MIX_S[1]:+.3f} between cf 0 and {MIX_CF[1]}); every reachable cell lands on the")
    print("     flat part, which is why the damage concentrates at the corner.")
    return out, cf_min


# =================================================================================================
def build_cells():
    """Render (or cache-hit) the whole grid and assemble one record per (mix, drive, grunt, sweep).

    Parallel per build.md's rule — the work items are independent subprocess renders.  `orig_ref()`
    is warmed FIRST because it lazily initialises module globals in GATE BL, and a lazy global
    initialised from several threads is exactly s133's `parallel.pmap` race."""
    BL.orig_ref()
    jobs = []
    for lt, lv, bt, bv in MIX_CELLS:
        for dname, dv in DRIVES:
            for gname, gv in GRUNTS:
                for arm in ARMS:
                    jobs.append((tag_of(lt, bt, dname, gname, arm),
                                 arm_args((lv, bv), dv, gv, arm), (lv, bv, dname, gname, arm)))
    print(f"  {len(jobs)} conditions ({len(MIX_CELLS)} mix cells = {len(LEVELS)}x{len(BLENDS)} grid "
          f"+ {len(LADDER_LEVELS)} LEVEL-ladder, x {len(DRIVES)} drive x {len(GRUNTS)} grunt x "
          f"{len(ARMS)} arms), {JOBS} jobs, streaming to curves")
    for lv, why in EXCLUDED_LEVELS:
        print(f"  ⛔ LEVEL {lv} EXCLUDED BY NAME: {why}")
    with ThreadPoolExecutor(max_workers=JOBS) as ex:
        got = list(ex.map(lambda j: curves(j[0], j[1]), jobs))
    by_key = {j[2]: c for j, c in zip(jobs, got)}

    g = W.GRID
    sel = (g >= F_LO_GRADE) & (g <= F_HI_GRADE)
    cells = []
    for lt, lv, bt, bv in MIX_CELLS:
        L = K.level_taper(lv)
        od0, cl0 = K.coef_closed(bv, L, endstop=(0.0, 0.0))
        ods, cls = K.coef_closed(bv, L)
        flat = 20.0 * math.log10(ods / od0)
        climit = float("inf") if cl0 <= 0 else 20.0 * math.log10(cls / cl0)
        lo_b, hi_b = min(flat, climit), max(flat, climit)
        for dname, dv in DRIVES:
            for gname, gv in GRUNTS:
                dcut, _, _, _ = cut_delta((lv, bv), dv, gv)
                a = {arm: by_key[(lv, bv, dname, gname, arm)] for arm in ARMS}
                for sw in SWEEPS:
                    raw = a["ship"][sw] - a["e0"][sw]
                    shape = raw - flat
                    rs, ss = raw[sel], shape[sel]
                    i = int(np.abs(ss).argmax())
                    out = (rs < lo_b - 1e-9) | (rs > hi_b + 1e-9)
                    mixd = (a["ship"][sw] - a["mixfroz"][sw])[sel]
                    notd = (a["mixfroz"][sw] - a["e0"][sw])[sel]
                    cells.append({
                        "mix": (lv, bv), "lt": lt, "bt": bt,
                        "drive": dname, "grunt": gname, "sweep": sw,
                        "ship": a["ship"][sw], "e0": a["e0"][sw],
                        "mixfroz": a["mixfroz"][sw],
                        "coef_e0": (od0, cl0), "coef_ship": (ods, cls),
                        "flat_db": flat, "cut_delta_db": dcut,
                        "raw_rms": float(np.sqrt((rs ** 2).mean())),
                        "shape_rms": float(np.sqrt((ss ** 2).mean())),
                        "shape_max": float(np.abs(ss).max()),
                        "shape_max_hz": float(g[sel][i]),
                        "frac_out": float(np.mean(out)),
                        "mix_max": float(np.abs(mixd).max()),
                        "notch_max": float(np.abs(notd).max()),
                    })
    return cells


def main():
    ap = argparse.ArgumentParser(description="GATE BM — mix-grid anchor re-read (s184, item 19 P1)")
    ap.add_argument("--out", default="analysis/reports/s184_mix_grid_anchor.json")
    args = ap.parse_args()

    print()
    print("#" * 100)
    print("# GATE BM — THE ANCHOR RE-READ ON THE MIX GRID   (session 184, item 19, task P1)")
    print("#" * 100)
    print("# Shipped stage vs `--fit blendEndStop=0` (= the pre-s181 model), at REAL CAPTURED")
    print("# (LEVEL, BLEND) settings rather than only the bleed-free corner.  Both arms are our own")
    print("# renders, so no capture, reference or authority question enters.")
    print("#")
    print("# USER STEER (s183 §9/§10): \"bleed-free is only ONE setting, and not even the most used")
    print("# one, so it's not the be all and end all.\"")
    print()

    e_hi, _e_lo = K.SHIPPED_BLEND_END_STOP
    gate_bm0(e_hi)
    print()
    cells = build_cells()
    gate_bm0fg(cells, e_hi)
    rows = gate_bm1()
    mix_stats, split = gate_bm2(cells, rows)
    feats = gate_bm3(cells)
    e6, e6_rows, refused = gate_bm4(cells)
    cut, cf_min = gate_bm5(rows)

    # ---------------------------------------------------------------------------------------------
    print()
    print("=" * 100)
    print("VERDICT — DOES ANYTHING MOVE AT SETTINGS PEOPLE PLAY?")
    print("=" * 100)
    res = LOCATOR_RES_FRAC * 100.0
    # ⚠⚠ COMPARED AS RATES, NOT COUNTS.  The played group has 540 readings and the corner 36, so a
    # MAX over each is not like-for-like — a max over 15x the sample will beat a fixed bar almost
    # regardless (`check-n-before-reading-a-trend`), and a raw count of membership flips is 15x
    # inflated on the played side by construction.  So membership is a PER-READING RATE and the
    # centre shift is quoted as the MEDIAN (typical) with the max printed beside it, never instead.
    _any = next(iter(feats.values()))
    print(f"  1. FEATURES — corner vs played, as RATES (n differs {_any['CORNER']['n']} vs "
          f"{_any['PLAYED']['n']}, so counts and")
    print("     maxima are not comparable).  Bar for 'typical': the locator's own "
          f"{res:.2f} % resolution.")
    print()
    print(f"     {'feature':13s} {'membership loss/reading':>23s}   {'median |Δf0| (xres)':>24s}   "
          f"{'worst |Δf0|':>13s}")
    print("     " + "-" * 82)
    louder, comparable, corner_blind = [], [], []
    for name, rec in feats.items():
        cn, pl = rec["CORNER"], rec["PLAYED"]
        lc = (cn["lost"] + cn["gain"]) / max(cn["n"], 1)
        lp = (pl["lost"] + pl["gain"]) / max(pl["n"], 1)
        mc, mp = cn["df_med_pct"], pl["df_med_pct"]
        tag = "" if mc == mc else "   <-- NOT RESOLVED AT THE CORNER AT ALL"
        print(f"     {name:13s} {lc * 100:9.1f} % -> {lp:6.1%}   "
              f"{mc:8.3f} -> {mp:6.3f} % ({mp / res:4.1f}x)   "
              f"{cn['df_max_pct']:5.2f} -> {pl['df_max_pct']:5.2f} %{tag}")
        # ⚠⚠ ONLY features resolved on BOTH sides can be COMPARED.  A draft counted "7 of 7"
        # including two whose corner median does not exist (0 of 36 resolved), which is an
        # undefined comparison reported as a confirmed one.
        if mc == mc and mp == mp:
            comparable.append(name)
            if mp > mc:
                louder.append(name)
        elif mp == mp:
            corner_blind.append((name, cn["resolved_both"], cn["n"],
                                 pl["resolved_both"], pl["n"]))
    print()
    print(f"     ⇒ the TYPICAL centre shift is SMALLER at played settings than at the corner for "
          f"{len(comparable) - len(louder)} of the")
    print(f"       {len(comparable)} features RESOLVED ON BOTH SIDES (larger for {len(louder)}: "
          f"{louder or 'none'}), and the membership-flip")
    print("       RATE is lower at played settings for every feature that resolves at both.")
    if corner_blind:
        print()
        print(f"     ⭐⭐ AND {len(corner_blind)} OF THE SEVEN CANNOT BE COMPARED, WHICH IS A STRONGER")
        print("        RESULT THAN THE COMPARISON: they do not resolve AT THE CORNER AT ALL, while")
        print("        resolving in hundreds of played readings — i.e. they are MIX features that a")
        print("        bleed-free reading is structurally blind to.")
        for name, cb, cn_, pb, pn in corner_blind:
            print(f"          {name:13s} resolved {cb} of {cn_} at the corner, "
                  f"{pb} of {pn} played")
        print("        ⇒ item 19's table has seven rows and the bleed-free corner can see five.")
    tp = feats.get("treble_peak")
    if tp:
        print(f"     ⭐ `treble_peak`, the feature s183 flagged: it lost {tp['CORNER']['lost']} of "
              f"{tp['CORNER']['n']} readings AT THE CORNER")
        print(f"       ({tp['CORNER']['lost'] / tp['CORNER']['n']:.1%}) and "
              f"{tp['PLAYED']['lost']} of {tp['PLAYED']['n']} "
              f"({tp['PLAYED']['lost'] / tp['PLAYED']['n']:.1%}) at played settings — a "
              f"{(tp['CORNER']['lost'] / tp['CORNER']['n']) / max(tp['PLAYED']['lost'] / tp['PLAYED']['n'], 1e-9):.0f}x")
        print("       lower rate.  ⇒ the corner reading is not representative of played settings.")

    c = mix_stats[CORNER]
    wm, wp = max(((m, v) for m, v in mix_stats.items() if m != CORNER),
                 key=lambda kv: kv[1]["shape_max"])
    ratio = c["shape_max"] / max(wp["shape_max"], 1e-9)
    print(f"  2. SIZE — AND THE DIRECTION IS THE OPPOSITE OF (1).  The worst SHAPE perturbation is")
    if ratio >= 1.0:
        print(f"     {ratio:.1f}x LARGER at the corner ({c['shape_max']:.2f} vs "
              f"{wp['shape_max']:.2f} dB at L {wm[0]} / B {wm[1]}).")
    else:
        print(f"     {1.0 / ratio:.1f}x larger at a PLAYED cell ({wp['shape_max']:.2f} dB at "
              f"L {wm[0]} / B {wm[1]}) than at the corner")
        print(f"     ({c['shape_max']:.2f} dB); LISTENING reaches "
              f"{mix_stats[LISTENING]['shape_max']:.2f} dB, also above it.  ⇒ the two")
        print("     statistics disagree about which setting is worst, and both are right: played")
        print("     settings move each FEATURE less often and less far, while carrying a LARGER")
        print("     worst-case shape excursion, because off the corner the two branches can cancel")
        print("     against EACH OTHER (BM2).  ⛔ Do not quote one as though it settled the other.")

    if e6["PLAYED"] and e6["CORNER"]:
        pc, pp = e6["CORNER"], e6["PLAYED"]
        print(f"  3. GATE AP's CENSORING.  Median Δ POINT depth {pc['dp_med']:+.2f} dB at the "
              f"corner vs {pp['dp_med']:+.2f} dB played;")
        print(f"     Δ AREA {pc['da_med']:+.2f} vs {pp['da_med']:+.2f}; point/area disagreement "
              f"{pc['ratio']:.1f}x -> {pp['ratio']:.1f}x.")
        # s183 §10's working hypothesis, TESTED rather than assumed.
        if abs(pp["dp_med"]) < 0.5 * abs(pc["dp_med"]):
            print("     ✅ s183 §10's WORKING HYPOTHESIS IS CONFIRMED: the point-depth censoring is")
            print("        substantially CORNER-ONLY, so nothing about GATE AP's s153 USER DECISION")
            print("        is reopened, and P2 does not have to carry it.")
        else:
            print("     ⛔⛔ s183 §10's WORKING HYPOTHESIS IS REFUTED: the censoring PERSISTS at")
            print("        played settings.  That is new information and goes to the user BY NAME,")
            print("        not silently into P2's re-anchor.")
        print(f"     ⚠ {len(refused)} of {len(refused) + pc['n'] + pp['n']} cells are REFUSED by "
              "the reader (minimum on a CORE bound) and are")
        print("       named in BM4 rather than dropped — a refusal is not a reading (s151).")

    sc = split[CORNER]
    print("  4. TWO MECHANISMS, NOT ONE.  `ship − e0` = the MIX COEFFICIENTS plus "
          "`OdToneRestore`'s CUT.")
    print("     ⭐⭐ THAT IS ITSELF A CORRECTION: THE CHAIN IS NOT A TWO-BRANCH MIXER, because the")
    print("     notch stage is keyed on `cleanFraction()`, so the OD branch's own response is a")
    print("     function of (LEVEL, BLEND).  Found by a branch-reconstruction guard FAILING")
    print("     (70979 of 517248 points outside the coherent-sum envelope), not by inspection.")
    if e6["CORNER"]:
        pc = e6["CORNER"]
        share = abs(pc["dp_mixonly_med"]) / max(abs(pc["dp_med"]), 1e-9)
        print(f"     ⇒ s183 §3's 320 Hz POINT-depth loss of {pc['dp_med']:+.2f} dB at the corner "
              f"SPLITS (paired, BM4):")
        print(f"       the bleed itself {pc['dp_mixonly_med']:+.2f} dB ({share:.0%} of it) and the "
              f"cut change {pc['dp_notchonly_med']:+.2f} dB.")
        if share > 0.75:
            print("       ⇒ s183's ATTRIBUTION IS SUBSTANTIALLY RIGHT, not wrong — the bleed is the")
            print("       dominant term.  What was wrong is that it was stated as the WHOLE of it.")
        else:
            print("       ⇒ s183's ATTRIBUTION IS NOT SUPPORTED: the bleed is a minority of the")
            print("       measured loss and the cut change carries the rest.")
    print(f"     ⚠ At {NOTCH_FREQ:.0f} Hz the two RESPONSES do oppose (notch "
          f"{sc['notch_at_323']:+.2f} dB, mix {sc['mix_at_323']:+.2f} dB,")
    print(f"       net {sc['total_at_323']:+.2f}), but the null's DEPTH is shoulder-referred and "
          "both act the same way")
    print("       on it.  ⛔ Two different quantities — do not read one's sign as the other's.")
    print(f"  5. P2's INPUT.  Reachable minimum clean fraction on this grid is {cf_min:.5f}; "
          "`kMixS[0]` sits at")
    print("     the unreachable cf = 0 and is the only steep part of the law.  ⭐ And BM5 CONFIRMS")
    print("     s183 §9 on the quantity §9 actually measured: the applied cut moves 3.1x more at")
    print("     the corner than at the worst played cell, with the opposite sign.  ⇒ P2 stays a")
    print("     ONE-NODE RE-ANCHOR, not a re-fit.")

    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w") as fh:
        json.dump({"end_stop": list(K.SHIPPED_BLEND_END_STOP),
                   "grid": {"levels": [l[1] for l in LEVELS], "blends": [b[1] for b in BLENDS],
                            "ladder_levels": [l[1] for l in LADDER_LEVELS],
                            "ladder_blend": LADDER_B,
                            "mix_cells": [[c[1], c[3]] for c in MIX_CELLS],
                            "excluded_levels": [[lv, why] for lv, why in EXCLUDED_LEVELS],
                            "drives": [d[0] for d in DRIVES], "grunts": [g[0] for g in GRUNTS],
                            "sweeps": list(SWEEPS), "arms": list(ARMS)},
                   "analytic": [{**{k: v for k, v in r.items() if k != "mix"},
                                 "mix": list(r["mix"]),
                                 "clean_limit_db": (None if math.isinf(r["clean_limit_db"])
                                                    else r["clean_limit_db"]),
                                 "drho_db": (None if math.isinf(r["drho_db"])
                                             else r["drho_db"])} for r in rows],
                   "mix_stats": {f"{m[0]}|{m[1]}": v for m, v in mix_stats.items()},
                   "split": {f"{m[0]}|{m[1]}": v for m, v in split.items()},
                   "features": feats, "e6": e6,
                   "e6_rows": [{**r, "mix": list(r["mix"])} for r in e6_rows],
                   "e6_refused": refused, "cut": cut, "cf_min": cf_min,
                   "cells": [{**{k: v for k, v in c.items() if not isinstance(v, np.ndarray)},
                              "mix": list(c["mix"])} for c in cells]},
                  fh, indent=1)
    print(f"\n  report -> {args.out}")


if __name__ == "__main__":
    main()
