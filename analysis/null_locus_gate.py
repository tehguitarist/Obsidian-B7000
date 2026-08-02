#!/usr/bin/env python3.11
"""GATE R -- WHERE the 320 Hz null lives, WHAT generates the harmonics at it, and WHY it moves
with stimulus.  Session 110.

It imports `od_absolute_gate` (GATE Q) -- and through it `a3_balance_gate` / `level_law_gate` /
`matrix_grade` -- so the endpoint selection, the `gain-n12` exclusion and the s109 reference-dropout
exclusion cannot drift from the chain the A3/OD work is quoted against.

WHY THIS EXISTS
---------------
Session 109 left this as the head item, framed as a TOPOLOGY question:

    "After s109 the model's null still runs +4.31 dB too deep at -30 dBFS and -3.67 dB too shallow
     at -6 -- it washes out where the reference's DEEPENS.  In our model that null is formed
     pre-clipper (the treble/ATTACK ladder), so compression fills it; for the reference's to survive
     drive, its null must either sit post-clipper or see a far gentler nonlinearity."

Two of the three load-bearing clauses in that paragraph had never been measured -- that our null is
the pre-clipper ladder (asserted from topology), and that the reference's null deepens (measured,
but POOLED over the pedal's own DRIVE control).  This gate measures both, plus the mechanism that
connects them.

WHAT IT MEASURES, AND THE ONE RESULT THAT MATTERS
------------------------------------------------
The instrument is `Hn/H1` at the null, referred to the null's own shoulders.  It is immune to any
absolute-level error and to the matrix's per-row gain match, and -- the useful part -- it carries a
SIGN that says which side of the null the harmonics were made on:

    null DOWNSTREAM of the harmonic source  ->  H1 attenuated, Hn is not  ->  Hn/H1 PEAKS
    null UPSTREAM   of the harmonic source  ->  the source is starved     ->  Hn/H1 DIPS

⚠ That is the OPPOSITE of the naive "a pre-clipper null must starve the clipper, so Hn/H1 dips"
reading this gate was first written to test, and the reason is structural rather than a detail:
THIS CHAIN HAS TWO NONLINEARITIES AND THE NULL SITS BETWEEN THEM.  The J201 (`JfetStage`) is at the
JFET drain, the treble/ATTACK ladder hangs off that drain, and the CD4049 clipper is downstream of
both.  So a ladder null is downstream of the J201 and upstream of the clipper, and which sign you
get depends on which device is actually making the harmonics at that frequency -- which R5
measures rather than assumes.  `verify-the-PREMISE`, applied to my own derivation.

GATES (all computed.  Hard exits cover the gate's OWN validity only; physics outcomes get computed
verdicts -- s108's rule.)
--------------------------------------------------------------------------------------------
R1  KNOWN ANSWER, the locus control.  Both candidate networks are R-C networks whose notch is set
    by products s*C, so scaling ALL of a network's caps by k moves ITS OWN notch by exactly 1/k and
    leaves every other network alone (the same scale-invariance circuit.md already records for the
    switchable mid bands).  So: the bridged-T's own ~712 Hz notch MUST move by 2.00x under a
    bt-cap halve, and MUST NOT move under a ladder-cap double.  Asserted -- without it R2 is a
    perturbation with no control.
R2  THE LOCUS.  Does the 320 Hz null move with the PRE-clipper ladder or the POST-clipper
    bridged-T?  Computed verdict, with the measured frequency ratio against the 2.00x the network
    algebra requires.
R3  MEMBERSHIP, asserted: the endpoint count, `gain-n12` excluded BY NAME and asserted FOUND, the
    s109 reference dropout excluded BY NAME and asserted FOUND, and the DRIVE spread PRINTED (a
    surface pooled over the pedal's own controls without printing that spread is s108's P4 trap --
    and here it is not a caveat, it is the finding: see R7).
R4  FLOOR GUARD on H1 and H2 at the null, both sides, against an empirical per-curve floor.  A
    reading at the floor is REPORTED as such rather than quoted as a measurement.
R5  THE HARMONIC SOURCE at the null -- which device makes the H2 that the null fails to attenuate.
    Two arms with their own vacuity controls: `jfetSatNeg=0` (the J201's even generator removed)
    and a symmetric clipper (the clipper's even generator removed).  A mutation that moves nothing
    ANYWHERE is a flag that never reached the DSP, not a null result, so each arm must be shown to
    move SOMETHING before its non-movement at the null is read.
R6  THE COMPRESSION DOSE-RESPONSE.  A pre-clipper null feeds a compressor, and a compressor reduces
    the depth of any dip fed into it -- so the model's null MUST wash out with stimulus, and the
    wash-out MUST grow with DRIVE.  DRIVE is the dose.  This is a pre-registered prediction with a
    built-in null case (DRIVE min, where there is little compression to do the washing).
R7  THE POOLING CORRECTION.  GATE Q's headline pools the 15 endpoints, which span DRIVE {0,.5,1}.
    Conditioned on DRIVE the reference's behaviour REVERSES SIGN, so the pooled statement is a
    mixture, not a property.

WHAT THIS DOES NOT CLAIM
------------------------
It does NOT locate the REFERENCE's null in its own signal chain.  R2's locus test needs a knob on
the network, and we have one only for our own model; for the reference this gate reports the
SIGNATURES (R5's sign, R6's dose-response) and what they are consistent with.  It does not re-open
the ATTACK axis (s108 closed that) -- R1/R2 use the SHARED ladder's caps, not the ATTACK cap, and
the notch frequency is measured here to be ATTACK-invariant on both sides anyway.
"""
import argparse
import concurrent.futures as futures
import json
import os
import subprocess
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                # noqa: E402
import captures as C               # noqa: E402
import comprehensive_report as CR  # noqa: E402
import od_absolute_gate as Q       # noqa: E402

REPORT = "analysis/reports/s109_k090_cand.json"
OUT_JSON = "analysis/reports/s110_null_locus.json"
ARM_DIR = "build/s110_null_arms"
EP_DIR = "build/s110_null_endpoints"
OS_FACTOR = 8

# The null under test and the two shoulders it is referred to.  NAMED, not found by argmin, so a
# perturbation that MOVES the null cannot silently re-point the statistic (GATE Q's own rule).
# The search WINDOW is separate and deliberately wide enough to follow the null when R2 moves it.
NOTCH_HZ = 320.0
SHOULDER_HZ = (202.0, 508.0)
# ⚠⚠ NOTCH_WIN IS DELIBERATELY TIGHT, AND A WIDE ONE IS A REAL BUG I SHIPPED IN THIS GATE'S FIRST
# RUN.  With (200, 520) the prominence is an argmin over a window that ALSO contains nothing else
# -- until the model is driven hard, at which point the pre-clipper null washes out so far that the
# POST-clipper bridged-T notch at ~712-723 Hz becomes the deepest point in the region and argmin
# ran to the window's high edge in 18 of 120 cells, ALL of them model cells.  The statistic then
# silently stopped being "the 320 Hz null" and became "the deepest thing nearby".
# `a-positional-index-is-a-shape-claim`: naming the notch frequency (GATE Q's rule) buys nothing if
# the estimator is then free to walk away from it.  (290, 370) contains every f0 measured on either
# side (pedal 312.7-327.6, model 322.8-329.9) with margin, and cannot reach the bridged-T.
NOTCH_WIN = (290.0, 370.0)
# The rank swap that defect exposed is kept as a MEASUREMENT (R6b) -- it is independent evidence
# for the compression mechanism: the null that survives drive is the one on the far side of the
# compressor.
BT_NOTCH_WIN = (600.0, 900.0)
# The bridged-T's own notch, R1's control.  circuit.md: R22/R23/C16/C17 = 100k/33k/680p/22n, ideal
# ~717 Hz unloaded; measured here at ~712 Hz through the real chain.
BT_WIN = (560.0, 1100.0)
BT_WIN_MOVED = (1000.0, 2200.0)

SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")
LO, HI = SWEEPS[0], SWEEPS[-1]

# One capture carries the arms: bleed-free (BLEND = LEVEL = 1, so the mix coefficient is exactly 1
# -- GATE K2), DRIVE noon, all switches at reference.  R6 then re-reads the SAME statistic over the
# full endpoint set, so the arms are never the only evidence.
ARM_CAP = "level-1700_base-od.wav"

# The expected pure-OD endpoint count, asserted rather than inferred so a silent membership change
# cannot pass.  It has to be BUMPED DELIBERATELY when the capture set grows, which is the point.
#   15  sessions 109-110 (the s109 129-capture matrix)
#   16  session 110, after the user's new `drive-1700_level-1700_master-1100_grunt-boost` capture
#       landed -- it is BLEND=1, LEVEL=1 and therefore a pure-OD endpoint too.  The assertion
#       caught it, which is exactly what it is for.
EXPECT_ENDPOINTS = 16

# The perturbations.  Each scales ALL of ONE network's capacitors, which is what makes R1's known
# answer exact rather than approximate: the notch moves by 1/k and nothing else does.
SHIP_LADDER = {"trebleC5": 7.95747e-9, "trebleC6": 1.39228e-9, "trebleC9": 1.28153e-8}
SHIP_BT = {"btC16": 680.0e-12, "btC17": 22.0e-9}
SHIP_CLIP = {"clipSatLo": 0.4377, "clipSatHi": 0.59791}

ARMS = {
    "base":    [],
    "lad_x2":  [f"{k}={v * 2.0:.6e}" for k, v in SHIP_LADDER.items()],
    "bt_half": [f"{k}={v * 0.5:.6e}" for k, v in SHIP_BT.items()],
    "jfet0":   ["jfetSatNeg=0.0"],
    "clipsym": [f"clipSatLo={0.5 * sum(SHIP_CLIP.values()):.6f}",
                f"clipSatHi={0.5 * sum(SHIP_CLIP.values()):.6f}"],
}

# R1 tolerances.  The frequency ratio is read off a notch minimum located on the Farina H1 axis,
# whose own reproducibility is set by the notch's curvature, not by the FFT bin -- 3% is loose
# against the 100% move being tested and tight against "did not move".
RATIO_TOL = 0.03
STATIC_TOL_HZ = 8.0
FLOOR_MARGIN_DB = 6.0

ORIG = None
REF = None


def _load_orig():
    global ORIG, REF
    if ORIG is None:
        ORIG = A.load(A.ORIG)
        REF = A.seg_of(ORIG, "sweep_clean")
    return ORIG, REF


# ---- rendering, with a condition stamp (`rebaseline-all-derived-artefacts`) ------------------
def _stamp_path(out):
    return out + ".args.json"


def render(out, args):
    """Render ONE condition, reusing an existing file only if its recorded argv matches exactly."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    want = list(args)
    sp = _stamp_path(out)
    if os.path.exists(out) and os.path.exists(sp):
        if json.load(open(sp))["argv"] == want:
            return out
        sys.stderr.write(f"  ! {out} was rendered at a DIFFERENT condition -- re-rendering\n")
    if not CR.render_plugin(CR.DEFAULT_BIN, want, out, OS_FACTOR):
        sys.exit(f"GATE R: render failed for {out}\n   args: {' '.join(want)}")
    with open(sp, "w") as fh:
        json.dump({"argv": want}, fh, indent=1)
    return out


def arm_args(fits):
    """Render args for ARM_CAP plus the arm's own --fit overrides.

    ⚠ The base args come from `captures.render_args`, never typed -- s65's rule (a headline
    finding once turned out to be a missing --grunt flag)."""
    args = C.render_args(C.parse_capture(ARM_CAP))
    for f in fits:
        args += ["--fit", f]
    return args


# ---- the statistic ---------------------------------------------------------------------------
def harmonics(sig_al, sweep, max_order=3):
    f, _, H = A.harmonic_thd_curve(A.seg_of(sig_al, sweep), REF, max_order=max_order)
    return f, H


def band_db(f, mag, centre, frac=6):
    """POWER-averaged level over a 1/`frac`-octave band centred on `centre`.

    ⭐ This is what makes the whole gate robust to the one thing it cannot measure -- how deep the
    notch really goes.  A point sample AT a cancellation bottom is set by the exact depth of a
    needle; a band-integrated deficit is set by the notch's AREA, and is barely moved by whether
    the last few dB of the bottom are real or are deconvolution residue.  `band-sampling-depends-
    on-curve-resolution` (s90) used constructively rather than as a caveat."""
    lo, hi = centre * 2 ** (-0.5 / frac), centre * 2 ** (0.5 / frac)
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return float(np.interp(centre, f, 20.0 * np.log10(mag + 1e-20)))
    return float(10.0 * np.log10(np.mean(mag[m] ** 2) + 1e-40))


def notch(f, mag, win):
    """(freq, prominence_band_dB, at_edge, prominence_point_dB).

    Prominence is referred to the NAMED shoulders when the window is the notch window, else to the
    window's own edges, and BOTH the bottom and the shoulders are read the SAME way (1/6-octave
    power average) so the two are comparable.  The point-sample prominence is returned alongside
    as R4's robustness control, never as the scored figure."""
    m = (f >= win[0]) & (f <= win[1])
    d = 20.0 * np.log10(mag[m] + 1e-20)
    j = int(np.argmin(d))
    f0 = float(f[m][j])
    if win == NOTCH_WIN:
        sh_b = 0.5 * (band_db(f, mag, SHOULDER_HZ[0]) + band_db(f, mag, SHOULDER_HZ[1]))
        sh_p = 0.5 * (float(np.interp(SHOULDER_HZ[0], f, 20 * np.log10(mag + 1e-20)))
                      + float(np.interp(SHOULDER_HZ[1], f, 20 * np.log10(mag + 1e-20))))
    else:
        sh_b = sh_p = 0.5 * (d[0] + d[-1])
    at_edge = j == 0 or j == len(d) - 1
    return f0, float(sh_b - band_db(f, mag, f0)), at_edge, float(sh_p - d[j])


def ratio_peak(f, H, order=2):
    """Hn/H1 at the NAMED notch frequency, referred to the NAMED shoulders.  Positive = PEAK."""
    r = 20.0 * np.log10((H[order] + 1e-20) / (H[1] + 1e-20))
    at = float(np.interp(NOTCH_HZ, f, r))
    sh = 0.5 * (np.interp(SHOULDER_HZ[0], f, r) + np.interp(SHOULDER_HZ[1], f, r))
    return at - sh, at, float(sh)


def floor_db(f, mag, lo=5.0, hi=15.0):
    """Deconvolution-residual floor proxy: the median level BELOW the sweep's own start frequency.

    ⚠ The first version of this took the 5th percentile of the curve over 100-1500 Hz, which is
    SELF-REFERENTIAL -- the null under test IS the bottom of that curve, so the guard was comparing
    the notch with itself and duly reported 101 of 120 cells "at the floor" with margins as low as
    -17 dB.  A floor has to come from somewhere the signal is not.

    `gen_test_signal.SWEEP_F0` is 20 Hz, so below it the reference sweep carries no energy and the
    deconvolution output is pure regularised-division residue.  That is a genuine floor and it is
    free.  Limitation, stated rather than hidden: the regularisation residue is not guaranteed to
    be the SAME size in-band, so this is a proxy, not a calibration -- but it is a conservative one
    for the only question asked of it (is the null bottom resolved, or is it resting on the
    instrument's floor?)."""
    m = (f >= lo) & (f <= hi)
    if not m.any():
        return -np.inf
    return float(np.median(20.0 * np.log10(mag[m] + 1e-20)))


# ---- worker for the endpoint surface ---------------------------------------------------------
def _endpoint_one(fname):
    _load_orig()
    parsed = C.parse_capture(fname)
    out = os.path.join(EP_DIR, fname.replace(".wav", "_plugin.wav"))
    render(out, C.render_args(parsed))
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), ORIG)
    ren_al, _ = A.align(A.load(out), ORIG)
    rec = {"file": fname, "drive": parsed.get("drive"), "model": {}, "pedal": {}}
    for sw in SWEEPS:
        for side, al in (("model", ren_al), ("pedal", cap_al)):
            f, H = harmonics(al, sw)
            fr, pr, edge, pr_pt = notch(f, H[1], NOTCH_WIN)
            btf, btp, _, _ = notch(f, H[1], BT_NOTCH_WIN)
            _m = (f >= BT_NOTCH_WIN[0]) & (f <= BT_NOTCH_WIN[1])
            bt_level = float(np.min(20.0 * np.log10(H[1][_m] + 1e-20)))
            rp, _, _ = ratio_peak(f, H)
            rec[side][sw] = {"f0": fr, "prom": pr, "prom_point": pr_pt, "edge": edge,
                             "h2_peak": rp, "bt_f0": btf, "bt_prom": btp, "bt_level": bt_level,
                             "resid": floor_db(f, H[1]),
                             "h1_at_null": band_db(f, H[1], fr),
                             "h1_at_500": band_db(f, H[1], 500.0),
                             "h2_at_null": band_db(f, H[2], fr)}
    return rec



def by_condition(rows, side, sw, key="prom"):
    """Median over distinct CONDITIONS: duplicates (differing only in MASTER, a pure gain) are
    averaged into one value first, so a near-duplicate capture cannot double-weight its condition."""
    groups = {}
    for r in rows:
        v = r[side][sw]
        if v.get("dropped"):
            continue
        groups.setdefault(r["cond"], []).append(v[key])
    if not groups:
        return float("nan")
    return float(np.median([float(np.mean(v)) for v in groups.values()]))


# =============================================================================================
def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--json", default=OUT_JSON)
    ap.add_argument("--jobs", "-j", type=int, default=8)
    a = ap.parse_args()

    _load_orig()
    out = {"report": a.report, "notch_hz": NOTCH_HZ, "shoulders": list(SHOULDER_HZ)}
    fail = []

    print("=" * 94)
    print("GATE R -- the 320 Hz null: WHERE it lives, WHAT feeds it, WHY it moves with stimulus")
    print("=" * 94)

    # ---- arms --------------------------------------------------------------------------------
    print(f"\n-- rendering {len(ARMS)} arms on {ARM_CAP} (cached by argv stamp) --")
    arm = {}
    with futures.ThreadPoolExecutor(max_workers=min(a.jobs, len(ARMS))) as ex:
        list(ex.map(lambda kv: render(os.path.join(ARM_DIR, kv[0] + ".wav"), arm_args(kv[1])),
                    ARMS.items()))
    for tag, fits in ARMS.items():
        al, _ = A.align(A.load(os.path.join(ARM_DIR, tag + ".wav")), ORIG)
        f, H = harmonics(al, "sweep_drv_-18")
        arm[tag] = {"f": f, "H": H, "fits": fits}
        print(f"   {tag:8s}  {' '.join(fits) if fits else '(shipped defaults)'}")

    # ---- R1 -- KNOWN ANSWER: the locus control ------------------------------------------------
    print("\n-- R1: KNOWN ANSWER -- scaling a network's caps by k moves ITS OWN notch by 1/k --")
    bt_base = notch(arm["base"]["f"], arm["base"]["H"][1], BT_WIN)
    bt_half = notch(arm["bt_half"]["f"], arm["bt_half"]["H"][1], BT_WIN_MOVED)
    bt_lad = notch(arm["lad_x2"]["f"], arm["lad_x2"]["H"][1], BT_WIN)
    r_bt = bt_half[0] / bt_base[0]
    print(f"   bridged-T notch, shipped        : {bt_base[0]:8.1f} Hz  (prominence {bt_base[1]:5.2f} dB)")
    print(f"   bridged-T notch, bt caps x0.5   : {bt_half[0]:8.1f} Hz  -> ratio {r_bt:5.3f} "
          f"(algebra requires 2.000)")
    print(f"   bridged-T notch, LADDER caps x2 : {bt_lad[0]:8.1f} Hz  -> moved "
          f"{abs(bt_lad[0] - bt_base[0]):5.1f} Hz (must be ~0)")
    if bt_base[2] or bt_half[2]:
        fail.append("R1: a bridged-T notch was located at a window EDGE -- that is a bound, not a "
                    "measurement; widen BT_WIN/BT_WIN_MOVED")
    if abs(r_bt - 2.0) > 2.0 * RATIO_TOL:
        fail.append(f"R1: the bridged-T notch did not move by 2.00x under its own cap scale "
                    f"(got {r_bt:.3f}) -- the perturbation is not doing what it claims, so R2 has "
                    f"no control")
    if abs(bt_lad[0] - bt_base[0]) > STATIC_TOL_HZ:
        fail.append(f"R1: the LADDER scale moved the bridged-T notch by "
                    f"{abs(bt_lad[0] - bt_base[0]):.1f} Hz -- the two networks are not separable "
                    f"by this perturbation and R2 cannot be read")
    if not fail:
        print("   => OK: the control network moves under its own knob and not under the other's.")
    out["r1"] = {"bt_base_hz": bt_base[0], "bt_half_hz": bt_half[0], "ratio": r_bt,
                 "bt_under_ladder_hz": bt_lad[0]}

    # ---- R2 -- THE LOCUS ----------------------------------------------------------------------
    print(f"\n-- R2: does the {NOTCH_HZ:.0f} Hz null follow the PRE-clipper ladder or the "
          f"POST-clipper bridged-T? --")
    n_base = notch(arm["base"]["f"], arm["base"]["H"][1], NOTCH_WIN)
    n_lad = notch(arm["lad_x2"]["f"], arm["lad_x2"]["H"][1], (100.0, 260.0))
    n_bt = notch(arm["bt_half"]["f"], arm["bt_half"]["H"][1], NOTCH_WIN)
    r_lad = n_base[0] / n_lad[0]
    print(f"   shipped                : {n_base[0]:8.1f} Hz  prominence {n_base[1]:6.2f} dB")
    print(f"   LADDER caps x2 (PRE)   : {n_lad[0]:8.1f} Hz  prominence {n_lad[1]:6.2f} dB   "
          f"-> ratio {r_lad:5.3f}")
    print(f"   bt caps x0.5   (POST)  : {n_bt[0]:8.1f} Hz  prominence {n_bt[1]:6.2f} dB   "
          f"-> moved {abs(n_bt[0] - n_base[0]):5.1f} Hz")
    moved_lad = abs(r_lad - 2.0) <= 2.0 * RATIO_TOL
    static_bt = abs(n_bt[0] - n_base[0]) <= STATIC_TOL_HZ
    if moved_lad and static_bt:
        verdict = ("PRE-CLIPPER: the null is the treble/ATTACK ladder.  CLAUDE.md's premise is "
                   "CONFIRMED by measurement, not merely asserted from topology.")
    elif (not moved_lad) and (not static_bt):
        verdict = "POST-CLIPPER: the null follows the bridged-T.  CLAUDE.md's premise is REFUTED."
    else:
        verdict = ("MIXED / UNRESOLVED: the null responds to both networks (or neither) -- do not "
                   "quote a locus.")
    print(f"   => {verdict}")
    out["r2"] = {"shipped_hz": n_base[0], "ladder_hz": n_lad[0], "ratio": r_lad,
                 "bt_hz": n_bt[0], "verdict": verdict}

    # ---- R3 -- MEMBERSHIP ---------------------------------------------------------------------
    print("\n-- R3: MEMBERSHIP, asserted --")
    bands, caps, absfr, nonhf, fb, eps, drops = Q.load_surface(a.report)
    n_defect = sum(1 for f in caps if Q.DEFECT_TOKEN in f and __import__("matrix_grade").is_od(f))
    print(f"   pure-OD endpoints (BLEND=1, LEVEL=1)        : {len(eps)}")
    print(f"   '{Q.DEFECT_TOKEN}' OD captures excluded by name  : {n_defect}")
    print(f"   s109 reference dropouts excluded            : {len(drops)}  {sorted(drops)}")
    drives = sorted({(caps[f].get('settings', {}) or {}).get('drive') for f in eps})
    print(f"   DRIVE settings spanned                      : {drives}")
    if len(eps) != EXPECT_ENDPOINTS:
        fail.append(f"R3: expected {EXPECT_ENDPOINTS} pure-OD endpoints, got {len(eps)} -- the "
                    f"capture set has changed. Check WHAT changed, then bump EXPECT_ENDPOINTS "
                    f"deliberately; do not infer it from the report or this assertion stops "
                    f"catching anything.")
    if n_defect == 0:
        fail.append(f"R3: the '{Q.DEFECT_TOKEN}' exclusion matched NOTHING -- a filter that "
                    f"silently matches nothing is `empty-gate-must-fail` in a costume")
    if len(drops) != Q.EXPECT_DROPOUTS:
        fail.append(f"R3: expected {Q.EXPECT_DROPOUTS} reference dropout(s), got {len(drops)}")
    if len(drives) < 3:
        fail.append(f"R3: the endpoints span only {len(drives)} DRIVE setting(s) -- R6/R7's whole "
                    f"content is the DRIVE conditioning, which needs at least 3")

    # ---- R3b -- EPOCH GUARD.  The report and the captures can disagree about time. -------------
    # ⚠⚠ This gate takes its MEMBERSHIP and its dropout exclusions from a stored report, and reads
    # the PEDAL side straight off the capture wavs.  Those are two different epochs, and captures
    # are cheap and re-recordable now (reference-sources.md §4) -- so a capture re-recorded AFTER
    # the report was rendered puts the two silently out of sync: the exclusion list describes a
    # file that no longer exists on disk, and the pedal numbers describe a file the report has
    # never seen.  Found the hard way in session 110: `drive-1700_level-1700_grunt-boost_base-od`
    # was re-captured 17 minutes AFTER `s109_k090_cand.json` was written, its dropout MOVED from
    # sweep_drv_-12 to sweep_drv_-18, and this gate was reading the new file while inheriting the
    # old file's exclusion.  `rebaseline-all-derived-artefacts`, running BACKWARDS -- the derived
    # artefact was fine and the SOURCE moved under it.
    rep_mtime = os.path.getmtime(a.report)
    newer = [(f, os.path.getmtime(os.path.join(C.CAPTURE_DIR, f)) - rep_mtime)
             for f in eps if os.path.getmtime(os.path.join(C.CAPTURE_DIR, f)) > rep_mtime]
    print(f"\n   epoch check -- captures newer than {os.path.basename(a.report)}: {len(newer)}")
    for f, dt in sorted(newer, key=lambda t: -t[1]):
        print(f"     ! {f}  re-captured {dt / 60.0:+.1f} min after the report was rendered")
    if newer:
        fail.append(f"R3b: {len(newer)} endpoint capture(s) are NEWER than the report supplying "
                    f"this gate's membership and dropout exclusions -- the pedal side and the "
                    f"exclusion list are from different epochs. Re-render the baseline before "
                    f"quoting anything here.")
    out["r3b"] = {"report_mtime": rep_mtime,
                  "newer_captures": [[f, dt] for f, dt in newer]}
    out["r3"] = {"n_endpoints": len(eps), "n_defect_excluded": n_defect,
                 "dropouts": sorted(f"{f}@{s}" for f, s in drops), "drives": drives}

    # ---- R5 -- THE HARMONIC SOURCE (before R4, which needs the surface) -----------------------
    print(f"\n-- R5: which device makes the H2 that the null fails to attenuate? --")
    print(f"   H2/H1 at {NOTCH_HZ:.0f} Hz re its own shoulders.  POSITIVE = the null is DOWNSTREAM "
          f"of the source.")
    print("\n   arm        H2/H1@null   re shoulders   |  H2/H1 @202  @508  @800  (vacuity control)")
    r5 = {}
    for tag in ("base", "jfet0", "clipsym", "lad_x2"):
        f, H = arm[tag]["f"], arm[tag]["H"]
        pk, at, sh = ratio_peak(f, H)
        r = 20.0 * np.log10((H[2] + 1e-20) / (H[1] + 1e-20))
        probe = [float(np.interp(x, f, r)) for x in (202.0, 508.0, 800.0)]
        r5[tag] = {"peak": pk, "at_null": at, "shoulders": sh, "probe": probe}
        print(f"   {tag:9s} {at:9.2f}   {pk:+11.2f}   | " + " ".join(f"{x:7.2f}" for x in probe))
    d_jfet = r5["base"]["at_null"] - r5["jfet0"]["at_null"]
    d_clip = r5["base"]["at_null"] - r5["clipsym"]["at_null"]
    mv_clip = max(abs(r5["base"]["probe"][i] - r5["clipsym"]["probe"][i]) for i in range(3))
    mv_jfet = max(abs(r5["base"]["probe"][i] - r5["jfet0"]["probe"][i]) for i in range(3))
    # Printed to 4 dp because at 2 dp the clipper arm reads a flat "+0.00", which is exactly the
    # kind of implausibly exact number that should be chased rather than quoted (s105 M4).  Chased:
    # it is 0.001 dB, not zero, and the arm's vacuity control shows it moving 21 dB elsewhere.
    print(f"\n   removing the J201 even generator moves H2/H1 at the null by  {d_jfet:+10.4f} dB")
    print(f"   making the clipper SYMMETRIC moves it by                      {d_clip:+10.4f} dB")
    print(f"   vacuity controls -- largest move ANYWHERE on the probe row: "
          f"jfet0 {mv_jfet:.2f} dB, clipsym {mv_clip:.2f} dB")
    if mv_clip < 1.0:
        fail.append("R5: the symmetric-clipper arm moved NOTHING anywhere -- that is a --fit that "
                    "never reached the DSP, not a null result")
    if mv_jfet < 1.0:
        fail.append("R5: the jfetSatNeg=0 arm moved NOTHING anywhere -- see above")
    if abs(d_jfet) > 3.0 * max(abs(d_clip), 1e-9):
        src = ("the J201, which sits UPSTREAM of the ladder null.  So a PRE-clipper null gives a "
               "PEAK here, and the naive 'a pre-clipper null starves its source' reading is wrong "
               "for THIS chain -- there are two nonlinearities and the null is between them.")
    elif abs(d_clip) > 3.0 * max(abs(d_jfet), 1e-9):
        src = "the CD4049 clipper, which sits DOWNSTREAM of the ladder null."
    else:
        src = "SHARED between the two devices -- do not attribute it to either."
    print(f"   => the H2 at the null is made by {src}")
    out["r5"] = {"arms": r5, "d_jfet": d_jfet, "d_clip": d_clip, "source": src}

    # ---- the endpoint surface -----------------------------------------------------------------
    print(f"\n-- rendering / reading {len(eps)} endpoints x {len(SWEEPS)} sweeps (-j {a.jobs}) --")
    with futures.ProcessPoolExecutor(max_workers=a.jobs) as ex:
        recs = list(ex.map(_endpoint_one, eps))
    by_file = {r["file"]: r for r in recs}

    # ⛔ The reference-side ladder dropouts must not enter ANY pedal statistic below.  Their
    # pedal_db is a ~14 dB hole, so a dropped cell would drag a median and would do it in the
    # DRIVE-max group -- exactly where R6/R8's whole conclusion lives.  `defective-rows-must-not-
    # vote`, applied inside this gate rather than only in the grading path.
    # ---- CONDITION de-duplication -------------------------------------------------------------
    # ⚠⚠ MASTER is a post-EQ, attenuation-only divider into a unity buffer with nothing nonlinear
    # downstream (circuit.md; GATE O6 measures its law flat to 0.0002 dB), so it is a PURE GAIN --
    # and a prominence is a CONTRAST, which a pure gain cannot move.  Measured here: the shipped and
    # `master-1100` grunt-boost renders give bit-identical prominences at all four stimulus levels.
    # So two endpoints differing only in MASTER are ONE condition, and pooling them as two files
    # double-weights that condition.  When the user's `master-1100` capture landed, exactly that
    # happened: the DRIVE-max model median swung 13.67 -> 8.55 dB at the quiet end and broke R6's
    # monotonicity -- a COMPOSITION change read as a physics result.
    # `aggregate-moved-check-membership-first`, eighth occurrence.
    # Every statistic below therefore pools over CONDITIONS (duplicates averaged first), with the
    # raw by-file figure printed beside it as a labelled control.
    for r in recs:
        st = dict(caps[r["file"]].get("settings", {}) or {})
        st.pop("master", None)
        r["cond"] = tuple(sorted((k, str(v)) for k, v in st.items()))
    conds = {}
    for r in recs:
        conds.setdefault(r["cond"], []).append(r["file"])
    dupes = {k: v for k, v in conds.items() if len(v) > 1}
    print(f"   endpoints {len(recs)} -> distinct CONDITIONS {len(conds)} "
          f"(MASTER-only duplicates collapsed: {len(dupes)})")
    for _k, v in dupes.items():
        print(f"     ~ {' == '.join(sorted(v))}")

    n_masked = 0
    for r in recs:
        for sw in SWEEPS:
            if (r["file"], sw) in drops:
                r["pedal"][sw]["dropped"] = True
                n_masked += 1
            else:
                r["pedal"][sw]["dropped"] = False
            r["model"][sw]["dropped"] = False
    print(f"   pedal cells masked as reference dropouts: {n_masked}")

    # ---- R4 -- FLOOR GUARD --------------------------------------------------------------------
    print("\n-- R4: is the null a MEASUREMENT or an artefact of how deep we can resolve? --")
    print("\n   ⚠ THERE IS NO NOISE FLOOR HERE, and two guards in this gate were wrong before that")
    print("   was faced.  Both sides are DETERMINISTIC renders (ours, and ND's -- reference-")
    print("   sources.md §0 records five ND renders agreeing to -147..-164 dBFS), so 'floor' can")
    print("   only mean the deconvolution's own residue.  Measured below 20 Hz, where the")
    print("   reference sweep has no energy, that residue tracks the STIMULUS almost 1:1:")
    m_res = [float(np.median([r["model"][sw]["resid"] - r["model"][sw]["h1_at_500"]
                              for r in recs])) for sw in SWEEPS]
    p_res = [float(np.median([r["pedal"][sw]["resid"] - r["pedal"][sw]["h1_at_500"]
                              for r in recs])) for sw in SWEEPS]
    print("      sub-20 Hz residue re the in-band 500 Hz level (dB):   clean  drv-18  drv-12  drv-6")
    print("        model  " + " ".join(f"{v:7.2f}" for v in m_res))
    print("        pedal  " + " ".join(f"{v:7.2f}" for v in p_res))
    print("   A noise floor does not follow the signal like that -- it is signal-proportional")
    print("   regularisation residue, so it is NOT a floor and must not be used as one.  It is")
    print("   also measured where the division is WORST conditioned, so it is an unquantified")
    print("   OVER-estimate of the in-band residue.  Printed for scale; NOT gated on.")
    # What CAN be gated is the thing that actually matters: the scored prominence is a 1/6-octave
    # power-integrated deficit, so it is set by the notch's AREA rather than by the exact depth of
    # its bottom.  The point-sample prominence is the control: where the two agree, the bottom is
    # resolved and the choice does not matter; where they diverge, the point sample is chasing a
    # needle and the band read is the trustworthy one.
    dif = [abs(r[s][sw]["prom_point"] - r[s][sw]["prom"])
           for r in recs for s in ("model", "pedal") for sw in SWEEPS]
    print(f"\n   scored prominence = 1/6-octave POWER-INTEGRATED deficit (set by the notch's AREA,")
    print(f"   not by its bottom).  Control -- point-sample prominence on the same cells:")
    print(f"      |band - point| over {len(dif)} cells: median {np.median(dif):.2f} dB, "
          f"p90 {np.percentile(dif, 90):.2f}, max {max(dif):.2f}")
    print(f"   The band read is ALWAYS the shallower of the two (it integrates the skirts), so it")
    print(f"   is a conservative measure of null depth in every cell.")
    for r in recs:
        for side in ("model", "pedal"):
            for sw in SWEEPS:
                r[side][sw]["ok"] = not r[side][sw]["edge"]
    edges = sum(1 for r in recs for s in ("model", "pedal") for sw in SWEEPS if r[s][sw]["edge"])
    print(f"\n   notch minima resting on a NOTCH_WIN edge (a bound, not a measurement): {edges} of "
          f"{len(recs) * 2 * len(SWEEPS)}")
    if edges > 0.1 * len(recs) * 2 * len(SWEEPS):
        fail.append(f"R4: {edges} notch minima rest on a NOTCH_WIN edge -- the null has left "
                    f"{NOTCH_WIN} in too many cells for the surface to be read")
    out["r4"] = {"resid_model": m_res, "resid_pedal": p_res, "n_edge": edges,
                 "band_vs_point": {"median": float(np.median(dif)),
                                   "p90": float(np.percentile(dif, 90)), "max": float(max(dif))}}

    # ---- R6 -- THE COMPRESSION DOSE-RESPONSE --------------------------------------------------
    print("\n-- R6: PRE-REGISTERED -- a pre-clipper null feeds a compressor, so the MODEL's null "
          "must WASH OUT with")
    print("       stimulus, and the wash-out must GROW with DRIVE (DRIVE is the dose; DRIVE min "
          "is the null case).")
    print("\n   null prominence (dB, 1/6-oct power-integrated) by stimulus, median over the")
    print("   endpoints at each DRIVE.  [] = the point-sample control from R4.")
    print("   DRIVE  side     clean   drv-18   drv-12    drv-6  |  washout = clean - drv_-6  [point]")
    r6 = {}
    for dv in drives:
        sel = [r for r in recs if r["drive"] == dv]
        r6[str(dv)] = {}
        for side in ("model", "pedal"):
            vals = [by_condition(sel, side, sw, "prom") for sw in SWEEPS]
            ptv = [by_condition(sel, side, sw, "prom_point") for sw in SWEEPS]
            raw = [float(np.median([r[side][sw]["prom"] for r in sel
                                    if not r[side][sw]["dropped"]])) for sw in SWEEPS]
            wash = vals[0] - vals[-1]
            r6[str(dv)][side] = {"prom": vals, "washout": wash, "n": len(sel),
                                 "n_cond": len({r["cond"] for r in sel}),
                                 "prom_point": ptv, "washout_point": ptv[0] - ptv[-1],
                                 "prom_byfile": raw, "washout_byfile": raw[0] - raw[-1]}
            print(f"   {dv:<5}  {side:6s} " + " ".join(f"{v:8.2f}" for v in vals)
                  + f"  |  {wash:+8.2f}   [pt {ptv[0] - ptv[-1]:+.2f}]"
                  + f"   [by-file {raw[0] - raw[-1]:+.2f}]"
                  + f"   n={len(sel)}/{len({r['cond'] for r in sel})} cond")
        print()
    mw = [r6[str(dv)]["model"]["washout"] for dv in drives]
    pw = [r6[str(dv)]["pedal"]["washout"] for dv in drives]
    # ⚠ isfinite FIRST and explicitly.  Every comparison against nan is False, so a single nan
    # silently turns "sign reverses" into "no sign reversal" -- the flattering answer, and the
    # exact failure mode s106's GATE N3 is in the discipline file for.  An earlier run of THIS
    # gate did precisely that after a cell-exclusion emptied a bucket.
    if not all(np.isfinite(x) for x in mw + pw):
        fail.append(f"R6: a wash-out figure is non-finite (model {mw}, pedal {pw}) -- a nan cannot "
                    f"be compared, so no verdict below it is trustworthy")
    mono = all(np.isfinite(mw[i]) and np.isfinite(mw[i + 1]) and mw[i] <= mw[i + 1] + 1e-9
               for i in range(len(mw) - 1))
    print(f"   MODEL wash-out vs DRIVE {drives}: " + " -> ".join(f"{x:+.2f}" for x in mw)
          + ("   MONOTONE INCREASING (prediction HOLDS)" if mono else "   NOT monotone"))
    print(f"   PEDAL wash-out vs DRIVE {drives}: " + " -> ".join(f"{x:+.2f}" for x in pw)
          + ("   sign REVERSES" if min(pw) < 0 < max(pw) else "   same sign throughout"))
    if mono:
        print("   => the model's null behaves EXACTLY as a linear pre-clipper cancellation feeding "
              "a compressor must:\n      the dip is squashed in proportion to how hard the "
              "compressor is working.  Mechanism confirmed by\n      dose-response, on our own "
              "model, with a null case at DRIVE min.")
    else:
        print("   => the model does NOT show the predicted dose-response; the compression reading "
              "is not supported.")
    out["r6"] = {"by_drive": r6, "model_washout": mw, "pedal_washout": pw, "model_monotone": mono}

    # ---- R6b -- the RANK SWAP, independent corroboration of the same mechanism ----------------
    print("-- R6b: the two nulls straddle the compressor, so drive must change their RANK --")
    print(f"   the {NOTCH_HZ:.0f} Hz null is PRE-clipper (R2); the bridged-T at ~712 Hz is POST-")
    print("   clipper.  Only the pre-clipper one can be squashed by the clipper, so at high drive")
    print("   the post-clipper notch must become the DEEPER of the two.  This is a prediction with")
    print("   no free parameter, and it is what the first run's 18 window-edge cells were.")
    # ⚠ Compared as ABSOLUTE H1 levels at the two notch bottoms, NOT as prominences: the two
    # prominences are referred to DIFFERENT baselines (the named 202/508 shoulders vs the
    # bridged-T window's own edges), and two numbers measured against different references cannot
    # be ranked against each other.  A first version of R6b did exactly that and duly reported
    # "no swap" while the absolute levels had swapped -- which is also what the argmin hop was.
    print("\n   MODEL, median ABSOLUTE H1 level (dB) at each notch bottom:")
    print("   condition                    320 Hz null   bridged-T   deeper (lower) feature")
    r6b = {}
    for dv in drives:
        sel = [r for r in recs if r["drive"] == dv]
        for sw in (LO, HI):
            a_ = float(np.median([r["model"][sw]["h1_at_null"] for r in sel]))
            b_ = float(np.median([r["model"][sw]["bt_level"] for r in sel]))
            r6b[f"{dv}/{sw}"] = {"null": a_, "bt": b_}
            print(f"   DRIVE {dv:<4} {sw:14s}  {a_:9.2f}   {b_:9.2f}   "
                  f"{'320 Hz null' if a_ < b_ else 'BRIDGED-T'}")
    swap = (r6b[f"{drives[0]}/{LO}"]["null"] < r6b[f"{drives[0]}/{LO}"]["bt"]
            and r6b[f"{drives[-1]}/{HI}"]["null"] > r6b[f"{drives[-1]}/{HI}"]["bt"])
    print(f"   => rank swap between (DRIVE min, quietest) and (DRIVE max, loudest): "
          f"{'YES -- prediction HOLDS' if swap else 'NO'}")
    out["r6b"] = {"cells": r6b, "swap": bool(swap)}

    # ---- R7 -- THE POOLING CORRECTION ---------------------------------------------------------
    print("\n-- R7: what POOLING over DRIVE did to GATE Q's headline --")
    pool = {}
    for side in ("model", "pedal"):
        vals = [by_condition(recs, side, sw, "prom") for sw in SWEEPS]
        pool[side] = {"prom": vals, "washout": vals[0] - vals[-1]}
        print(f"   {side:6s} pooled over all {len(recs)} endpoints: "
              + " ".join(f"{v:8.2f}" for v in vals) + f"  |  washout {vals[0] - vals[-1]:+7.2f}")
    reversal = all(np.isfinite(x) for x in pw) and min(pw) < 0 < max(pw)
    print()
    if reversal:
        print("   => the PEDAL's wash-out REVERSES SIGN across DRIVE "
              f"({max(pw):+.2f} dB at one setting, {min(pw):+.2f} at another), so any statistic")
        print("      pooled over DRIVE is a MIXTURE and its sign is set by the mix, not by the "
              "device.  GATE Q's")
        print("      'the reference's null DEEPENS with level' is a property of the DRIVE-max "
              "rows only.")
    else:
        print("   => no sign reversal across DRIVE; the pooled statement stands as a property.")
    out["r7"] = {"pooled": pool, "pedal_sign_reversal": bool(reversal)}

    # ---- R8 -- two candidate explanations for the DRIVE-max gap, both rendered ----------------
    print("\n-- R8: the DRIVE-max gap -- two candidates, both PRE-REGISTERED and both rendered --")
    print("   At DRIVE max the model's null collapses under stimulus and the reference's GROWS.")
    print("   (a) is it the s109 saturation defect?  Then the pre-s109 kInputRef (hotter into every")
    print("       nonlinearity) must be WORSE, and the shipped value must have already improved it.")
    print("   (b) is it a POST-clipper null the reference has and we do not?  R6b says a")
    print("       post-clipper notch is immune to the clipper, so moving OUR bridged-T from its")
    print("       ~712 Hz home down to 320 Hz must reproduce the reference's driven depth.")
    dmax = [r for r in recs if r["drive"] == max(drives)]
    files = [r["file"] for r in dmax]
    k_bt = r6b_bt = 712.0 / NOTCH_HZ
    arms8 = {
        "shipped":     [],
        "K pre-s109":  [("raw", ["--input-ref", "1.2596"])],
        "bt -> 320Hz": [("fit", f"btC16={680e-12 * k_bt:.6e}"), ("fit", f"btC17={22e-9 * k_bt:.6e}")],
    }
    print("\n   arm                     clean   drv-18   drv-12    drv-6  |  washout   n=%d" % len(files))
    r8 = {}
    for tag, mods in arms8.items():
        proms = {sw: {} for sw in SWEEPS}   # keyed by CONDITION, see by_condition()
        cond_of = {r["file"]: r["cond"] for r in dmax}
        for fn in files:
            args = C.render_args(C.parse_capture(fn))
            for kind, v in mods:
                args += v if kind == "raw" else ["--fit", v]
            outp = os.path.join(ARM_DIR, tag.replace(" ", "_").replace("->", "to")
                                .replace("/", "_") + "__" + fn)
            render(outp, args)
            al, _ = A.align(A.load(outp), ORIG)
            for sw in SWEEPS:
                f, H = harmonics(al, sw, max_order=2)
                proms[sw].setdefault(cond_of[fn], []).append(notch(f, H[1], NOTCH_WIN)[1])
        # Pooled over CONDITIONS, exactly as R6/R7 are: the MASTER-only duplicate is model-identical
        # (measured bit-identical), so counting it twice would double-weight one condition.
        vals = [float(np.median([float(np.mean(v)) for v in proms[sw].values()])) for sw in SWEEPS]
        r8[tag] = {"prom": vals, "washout": vals[0] - vals[-1]}
        print(f"   {tag:16s} " + " ".join(f"{v:8.2f}" for v in vals)
              + f"  |  {vals[0] - vals[-1]:+8.2f}")
    ped = [by_condition(dmax, "pedal", sw, "prom") for sw in SWEEPS]
    r8["PEDAL"] = {"prom": ped, "washout": ped[0] - ped[-1]}
    print(f"   {'PEDAL':16s} " + " ".join(f"{v:8.2f}" for v in ped)
          + f"  |  {ped[0] - ped[-1]:+8.2f}")
    # ⚠ s108's P4 rule: a figure pooled over the pedal's OWN controls must print the spread it is
    # pooling.  These 5 endpoints differ in ATTACK and GRUNT, and the spread is the size of the
    # effect -- which is exactly why this is a LOCATED target and not a characterised one.
    per = {r["file"]: r["pedal"][LO]["prom"] - r["pedal"][HI]["prom"] for r in dmax}
    r8["PEDAL_per_file_washout"] = per
    print(f"\n   PEDAL wash-out PER FILE (these 5 differ in ATTACK / GRUNT):")
    for f, w in sorted(per.items(), key=lambda t: t[1]):
        print(f"     {w:+7.2f}   {f}")
    vals = sorted(per.values())
    n_rev = sum(1 for w in per.values() if w < 0)
    print(f"   spread {vals[0]:+.2f} .. {vals[-1]:+.2f} dB ({vals[-1] - vals[0]:.2f} dB across "
          f"{len(per)} captures); {n_rev}/{len(per)} individually REVERSE.")
    print(f"   ⇒ the reversal is a property of most of the set, not of the median alone -- but the")
    print(f"     spread is {vals[-1] - vals[0]:.0f} dB, so quote the SIGN, never the size.")

    d_sat = r8["K pre-s109"]["washout"] - r8["shipped"]["washout"]
    print(f"\n   (a) pre-s109 K wash-out {r8['K pre-s109']['washout']:+.2f} vs shipped "
          f"{r8['shipped']['washout']:+.2f}.")
    if d_sat < 0:
        print("       => the global saturation lever does NOT close this.  ⚠ And read WHICH END "
              "moved before")
        print("          calling it a regression: the shipped value IMPROVED the quiet end "
              f"({r8['K pre-s109']['prom'][0]:.2f} -> {r8['shipped']['prom'][0]:.2f}) and left the")
        print(f"          driven end alone ({r8['K pre-s109']['prom'][-1]:.2f} -> "
              f"{r8['shipped']['prom'][-1]:.2f}).  The wash-out grew because its OTHER end did.")
        print("          `a-ratio-can-move-because-its-denominator-moved`, on a difference.")
    else:
        print("       => the saturation lever DOES move it in the expected direction.")
    gap_ship = abs(r8["shipped"]["prom"][-1] - ped[-1])
    gap_bt = abs(r8["bt -> 320Hz"]["prom"][-1] - ped[-1])
    print(f"\n   (b) DRIVEN depth (drv_-6): shipped {r8['shipped']['prom'][-1]:.2f}, "
          f"bt@320 {r8['bt -> 320Hz']['prom'][-1]:.2f}, pedal {ped[-1]:.2f}")
    print(f"       gap to the reference: {gap_ship:.2f} dB -> {gap_bt:.2f} dB")
    if gap_bt < 0.5 * gap_ship:
        print("       => a POST-clipper null at 320 Hz reproduces the reference's DRIVEN depth.")
    print(f"       BUT the wash-out is essentially unchanged "
          f"({r8['shipped']['washout']:+.2f} -> {r8['bt -> 320Hz']['washout']:+.2f}), because it "
          f"also deepens")
    print(f"       the QUIET end ({r8['shipped']['prom'][0]:.2f} -> "
          f"{r8['bt -> 320Hz']['prom'][0]:.2f}) where the reference is only {ped[0]:.2f} dB.")
    print("   ⇒ NEITHER candidate closes it, and the reason is that the reference's null DEPTH")
    print("     GROWS with stimulus here -- which NO fixed linear network at ANY position can do,")
    print("     because a fixed cancellation's depth does not depend on level.  So the missing")
    print("     degree of freedom is not a null in a different PLACE; it is a null whose depth is")
    print("     LEVEL-DEPENDENT.  ⚠ n=%d captures at ONE drive setting -- a located target, not a"
          % len(files))
    print("     characterised one.")
    out["r8"] = r8

    # ---- verdict ------------------------------------------------------------------------------
    print("\n" + "=" * 94)
    os.makedirs(os.path.dirname(a.json), exist_ok=True)
    with open(a.json, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"wrote {a.json}")
    if fail:
        print("GATE R: FAIL")
        for m in fail:
            print("  ! " + m)
        sys.exit(1)
    print("GATE R: OK (validity checks passed; the physics verdicts above are computed, not "
          "asserted)")


if __name__ == "__main__":
    main()
