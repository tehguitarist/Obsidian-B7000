#!/usr/bin/env python3.11
"""GATE W -- the peak/notch CENTRE-FREQUENCY audit, and the MIX-vs-NETWORK discriminator.
Session 122.

It imports `od_absolute_gate` (GATE Q) -- and through it `a3_balance_gate` / `level_law_gate` /
`matrix_grade` -- so the pure-OD endpoint selection, the reference-dropout detection and the
`gain-n12` handling cannot drift from the chain every OD number is quoted against.

WHY THIS EXISTS
---------------
Session 119/120 recorded a user chart review of model-vs-ND-capture OD frequency responses which
flagged SIX peak/notch CENTRE-frequency mismatches -- not depths, centres.  It was explicitly
logged as "NOTHING BELOW IS A GATED FINDING ... a work-list for the next dedicated session", with
two instructions attached:

    "check EVERY peak/notch centre on EVERY OD capture, not just the six features spotted by eye"
    "TEMPER every mismatch against reference-sources.md's HW-vs-ND authority split before booking
     it as a model defect"

THE QUESTION THIS GATE ASKS FIRST, AND WHY IT COMES FIRST
---------------------------------------------------------
A centre-frequency mismatch is only a NETWORK-CORNER error if the feature is made by a network.
This chain's output is a two-source mix -- `a(B,L)*OD + b(B,L)*CLEAN` (GATE K2) -- and a mix of two
paths produces CANCELLATION features that belong to neither path.  Those have a centre set by where
the two paths are equal-and-opposite, i.e. by the OD/clean BALANCE, which is A3.

The two are told apart with no threshold at all, because they respond differently to a knob that
changes only the mix:

    a MIX CANCELLATION      moves with LEVEL, and vanishes at LEVEL max (bleed exactly zero, K2)
    a NETWORK CORNER        cannot move with LEVEL at all -- LEVEL is downstream of every filter

⇒ W4 sweeps the LEVEL ladder on BOTH sides and classifies every feature before W5 reads any
mismatch as a defect.  Getting this backwards would book the OD/clean balance as a filter error and
point an optimiser at whichever cap sits nearest the flagged frequency.

GATES (all computed.  Hard exits cover the gate's OWN validity only; physics outcomes get computed
verdicts -- s108's rule.)
--------------------------------------------------------------------------------------------
W1  KNOWN ANSWERS for the locator itself, two of them, before anything is read off it.
    (a) It must reproduce GATE R's stored notch frequencies -- the 320 Hz null (329.727 Hz) and the
        bridged-T (712.006 Hz) -- on GATE R's own capture.  GATE R locates a notch by argmin on the
        raw 0.046 Hz Farina grid; this gate power-averages onto a 1/48-octave log grid and
        parabola-interpolates the vertex in log-f.  Two estimators sharing no arithmetic.
    (b) THE PHYSICS KNOWN ANSWER, which is what makes (a) non-vacuous: both candidate networks are
        R-C, so scaling ALL of one network's caps by k moves ITS OWN notch by exactly 1/k and
        leaves the other alone (GATE R's R1, reused here as a test of the LOCATOR rather than of
        the topology).  Doubling the ladder caps MUST halve the mid notch and MUST NOT move the
        bridged-T.  A locator that is really tracking something else fails this.
W2  MEMBERSHIP, asserted -- never inferred, or it stops catching anything.  The LEVEL ladder
    resolved by SETTINGS (not by filename: LEVEL noon is `ref-od.wav`, s112's twin-resolution
    lesson), the pure-OD endpoints taken from GATE Q, the `gain-n12` group and the reference
    dropouts excluded BY THE SHARED DEFINITIONS and asserted FOUND, and LEVEL min excluded because
    the MODEL MUTES there (GATE L7) -- with the mute MEASURED rather than assumed.
W3  WINDOW VALIDITY.  Every feature is located inside a NAMED window (GATE Q/R's rule: a named
    feature cannot be silently re-pointed by a candidate that moves it).  A window is only valid
    while no measurement rests on its edge and it cannot reach a neighbouring feature -- both
    asserted, with the worst margin printed.  The grid's own resolution is printed beside every
    quoted ratio so a 1 % mismatch is never read as a measurement.
W4  THE DISCRIMINATOR: the LEVEL dose-response, both sides.  Computed verdict per feature:
    MIX (moves with LEVEL) / NETWORK (does not) / UNRESOLVED.
W5  THE BLEED-FREE OD-PATH READ.  At BLEND = LEVEL = 1 the mix coefficient is exactly 1 and the
    clean tap is exactly 0 (K2's two exact zeros), so this is the OD path with no mix at all.
    Model-vs-pedal centre RATIO per surviving feature.  This is the audit's actual answer.
W6  STIMULUS DEPENDENCE.  A fixed linear network's centre frequency cannot depend on how hard the
    chain is driven.  Anything that moves across the 24 dB stimulus ladder is drive-GENERATED, not
    a corner -- which is the HF region GATE I already attributes to ND.
W7  THE HW-vs-ND CLASSIFICATION the user asked for, applied to what survives W4-W6.

WHAT THIS DOES NOT CLAIM
------------------------
It does not fit anything and proposes no constant.  It does not locate the REFERENCE's features in
the reference's own signal chain -- ND is a black box, so for the pedal this gate reports the
SIGNATURES (W4's dose-response, W6's stimulus dependence) and what they are consistent with.
Where a mismatch survives every discriminator it is reported as a located target, NOT as a
diagnosis of which element carries it.
"""
import argparse
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import analyze as A                # noqa: E402
import captures as C               # noqa: E402
import comprehensive_report as CR  # noqa: E402
import matrix_grade as MG          # noqa: E402
import od_absolute_gate as Q       # noqa: E402
import null_locus_gate as R        # noqa: E402  (for EXPECT_ENDPOINTS -- ONE definition)
from parallel import pmap          # noqa: E402

REPORT = "analysis/reports/s120_newton.json"
OUT_JSON = "analysis/reports/s122_feature_locus.json"
REN_DIR = "build/s122_feature_locus"
ARM_DIR = "build/s122_feature_arms"
OS_FACTOR = 8

SWEEPS = ("sweep_clean", "sweep_drv_-18", "sweep_drv_-12", "sweep_drv_-6")

# ---- the log-frequency grid -------------------------------------------------------------------
# 1/48 octave = 1.45 % per cell, power-averaged over each cell's own width, then the vertex is
# parabola-interpolated in log-f.  Two reasons for the smoothing, both load-bearing:
#   * the raw Farina grid is 0.046 Hz, so a bare argmin on it is set by a single bin at the bottom
#     of a cancellation needle -- `band-sampling-depends-on-curve-resolution` (s90), used the way
#     GATE R's `band_db` uses it: an AREA-weighted read, not a needle read;
#   * 1/48 octave is 18x finer than the 1/3-octave grade grid that
#     `peak-frequency-needs-subband-interpolation` warns about, and W1 measures what it actually
#     resolves rather than asserting it.
GRID_FRAC = 48
F_LO, F_HI = 22.0, 17000.0

# ---- THE NAMED FEATURES ------------------------------------------------------------------------
# ⚠⚠ THESE WINDOWS ARE DERIVED, NOT CHOSEN.  They come from an exploratory pass over the LEVEL
# ladder and the pure-OD endpoints at all four stimulus levels, and each one is required to contain
# every f0 measured on EITHER side with margin while being unable to reach the next feature along.
# W3 asserts both properties on every run, so a capture set that grows past a window fails loudly
# instead of silently reporting a feature resting on an edge (`a-positional-index-is-a-shape-claim`
# -- naming the feature buys nothing if the estimator may then walk out of its window).
#
# `kind`  min = notch, max = peak.
# `label` is the user's own name for it in the session-119 chart-review table.
FEATURES = (
    ("bass_notch",   "min", (30.0, 110.0),     "bass notch (~63 model / ~50 ND)"),
    ("bass_peak",    "max", (110.0, 285.0),    "bass peak (~150-200)"),
    ("mid_notch",    "min", (285.0, 358.0),    "320 Hz null (GAP #2)"),
    ("mid_peak",     "max", (358.0, 620.0),    "mid peak (~403-420 ND / ~530 model)"),
    ("bt_notch",     "min", (620.0, 1000.0),   "recovery bridged-T (~712)"),
    ("treble_peak",  "max", (1800.0, 4200.0),  "treble peak (~2-3k)"),
    ("treble_notch", "min", (4200.0, 12000.0), "treble notch (~5k model / ~6.3k ND)"),
)
FEAT_BY_NAME = {f[0]: f for f in FEATURES}

# W1(a): GATE R's own stored figures, READ from its report rather than transcribed
# (`rebuild-targets-dont-transcribe`).  The tolerance is on the RATIO, and it is loose against the
# 2.00x move W1(b) tests and tight against "the locator is tracking a different feature".
GATE_R_REPORT = "analysis/reports/s110_null_locus.json"
GATE_R_ARM_CAP = "level-1700_base-od.wav"
# ⚠⚠ GATE R's CONDITION IS NAMED, NOT SEARCHED FOR, AND THE FIRST DRAFT OF THIS GATE GOT THAT
# WRONG IN THE MOST INSTRUCTIVE WAY.  It picked the sweep whose reading agreed BEST with GATE R's
# stored number -- `self-selecting-scores`, committed inside the known answer written to validate
# the locator.  It duly selected `sweep_clean` (which minimises the MID-notch error) and then read
# the BRIDGED-T at that same sweep, where the bridged-T notch has a prominence of 0.46 dB and is
# barely a feature at all: 659.8 Hz against GATE R's 712.0, a 7.3 % "FAIL" that was nothing to do
# with the locator.  GATE R builds its arms at `sweep_drv_-18` (`null_locus_gate.py`, the arm loop),
# so that is the condition, stated.
GATE_R_SWEEP = "sweep_drv_-18"
# ⚠ The two gates read DIFFERENT H1s of the same deconvolution and `analyze.py` says in as many
# words that they "must not be quoted interchangeably": GATE R uses `harmonic_thd_curve`'s +-40 ms
# Hann H1, this gate uses `transfer_h1`'s +-350 ms Tukey H1.  That is a real instrument difference
# (~25 Hz vs ~3 Hz of spectral smearing), so agreement here is EVIDENCE rather than bookkeeping --
# measured at GATE R's own condition it is 0.10 % on the mid notch and 0.02 % on the bridged-T.
KA_TOL_FRAC = 0.02

# W1(b): the ladder caps, from GATE R's own constant so the two gates cannot drift.
SHIP_LADDER = {"trebleC5": 7.95747e-9, "trebleC6": 1.39228e-9, "trebleC9": 1.28153e-8}
SCALE_TOL = 0.04          # on the measured 1/k ratio
STATIC_TOL_FRAC = 0.02    # on the network that must NOT move
# ⚠ The moved notch needs its OWN window -- a named window is a claim about where the feature is,
# and doubling the caps deliberately moves it out of the shipped one.  GATE R uses (100, 260) for
# exactly this arm; same here, so the two gates follow the same feature.  A second draft of W1b
# located the "moved" notch inside the SHIPPED window and reported a ratio of 1.09 -- that was the
# window failing to contain the feature, not the locator failing to track it, and it is the same
# class of error as the sweep-selection one above: the reading looked plausible (302 Hz, not near
# an edge) because `locate` always returns SOMETHING.  W1b now applies W3's own validity guards.
MID_WIN_MOVED = (100.0, 260.0)

# W3: a located vertex this close to its window edge is not a measurement.
EDGE_MARGIN_FRAC = 0.04
# W3: AND NEITHER IS A VERTEX ON A FEATURE THAT IS NOT THERE.  `locate` always returns the extremum
# of its window, so on a curve with no notch in that region it returns an inflection -- which is
# exactly how the first run of W1 "measured" the bridged-T at 659.8 Hz on `sweep_clean`, where its
# prominence is 0.46 dB.  A located centre is only a measurement while the feature has some depth.
# The bar is swept and the surviving count asserted to CHANGE (s106's N5: a robustness sweep whose
# knob never turns is a constant printed N times), and the distribution is printed so it can be
# checked for the gap the bar sits in.
MIN_PROM_DB = 1.0
PROM_SWEEP = (0.5, 1.0, 2.0, 4.0)
# W4: the LEVEL span a centre must move by before it is called MIX.  Placed against the locator's
# own measured resolution (W1) rather than chosen -- see `gate_w4`.
MIX_MOVE_FRAC = 0.05
# W6: the same bar applied across the stimulus ladder.
STIM_MOVE_FRAC = 0.05

# LEVEL min: the MODEL MUTES (GATE L7 -- `divRatio(0)` is exactly 0 and the shipped stage sets the
# wiper hard on VD), so the row carries no locatable feature on the model side at all.  Excluded --
# but the mute is MEASURED in W2, not assumed, because "excluded because we expect silence" is how
# a genuinely broken render gets waved through.
SILENT_DB = -120.0

ORIG = None
REF = None


def _load_orig():
    global ORIG, REF
    if ORIG is None:
        ORIG = A.load(A.ORIG)
        REF = A.seg_of(ORIG, "sweep_clean")
    return ORIG, REF


# ---- rendering, with a condition AND BINARY stamp ---------------------------------------------
def _bin_sig():
    st = os.stat(CR.DEFAULT_BIN)
    return [st.st_size, st.st_mtime_ns]


def render(out, args):
    """Render one condition, reusing an existing file only if its recorded argv AND BINARY match.

    The binary half is not optional: session 117 found GATE R silently re-reading renders of a
    superseded build because its stamp covered argv only (`rebaseline-all-derived-artefacts`, in
    its baseline-EPOCH form).  This gate is new, so it gets the repaired stamp from the start."""
    os.makedirs(os.path.dirname(out), exist_ok=True)
    sp = out + ".args.json"
    want = list(args)
    if os.path.exists(out) and os.path.exists(sp):
        st = json.load(open(sp))
        if st["argv"] == want and st.get("bin") == _bin_sig():
            return out
        why = "a DIFFERENT condition" if st["argv"] != want else "a DIFFERENT BINARY"
        sys.stderr.write(f"  ! {out} was rendered at {why} -- re-rendering\n")
    if not CR.render_plugin(CR.DEFAULT_BIN, want, out, OS_FACTOR):
        sys.exit(f"GATE W: render failed for {out}\n   args: {' '.join(want)}")
    with open(sp, "w") as fh:
        json.dump({"argv": want, "bin": _bin_sig()}, fh, indent=1)
    return out


# ---- the locator -------------------------------------------------------------------------------
def log_grid(frac=GRID_FRAC, lo=F_LO, hi=F_HI):
    n = int(np.ceil(np.log2(hi / lo) * frac))
    return lo * 2.0 ** (np.arange(n + 1) / frac)


GRID = log_grid()
LOG_GRID = np.log(GRID)
GRID_STEP_FRAC = 2.0 ** (1.0 / GRID_FRAC) - 1.0


def smooth(f, mag_db, grid=GRID, frac=GRID_FRAC):
    """POWER-average the Farina curve into each log cell -> dB on `grid`."""
    p = 10.0 ** (np.asarray(mag_db) / 10.0)
    lo = grid * 2.0 ** (-0.5 / frac)
    hi = grid * 2.0 ** (+0.5 / frac)
    il = np.searchsorted(f, lo)
    ih = np.maximum(np.searchsorted(f, hi), il + 1)
    csum = np.concatenate([[0.0], np.cumsum(p)])
    return 10.0 * np.log10((csum[ih] - csum[il]) / (ih - il) + 1e-30)


def locate(d, win, kind, grid=GRID):
    """Locate ONE named feature inside its window.

    -> dict(f0, value, prominence, edge, margin_frac).  `f0` is the parabola-interpolated vertex in
    LOG frequency, which is the coordinate the feature actually lives in (a peak is symmetric in
    log-f for an R-C network, not in linear f) -- `peak-frequency-needs-subband-interpolation`.
    `edge` is True when the extremum sits within EDGE_MARGIN_FRAC of a window bound, i.e. when the
    window is a BOUND rather than a measurement."""
    m = (grid >= win[0]) & (grid <= win[1])
    idx = np.flatnonzero(m)
    dd = d[m] if kind == "min" else -d[m]
    j = int(np.argmin(dd))
    i = idx[j]
    at_edge = j == 0 or j == len(dd) - 1
    # prominence: rise out of the extremum before the curve turns back past it, both directions
    left = right = 0.0
    for k in range(j - 1, -1, -1):
        left = max(left, dd[k] - dd[j])
        if dd[k] < dd[j]:
            break
    for k in range(j + 1, len(dd)):
        right = max(right, dd[k] - dd[j])
        if dd[k] < dd[j]:
            break
    prom = float(min(left, right))
    if 0 < i < len(d) - 1:
        # Negate for a peak so the vertex fit is always the same minimum-parabola, in log-f.
        y0, y1, y2 = (-d[i - 1], -d[i], -d[i + 1]) if kind == "max" else (d[i - 1], d[i], d[i + 1])
        den = y0 - 2 * y1 + y2
        dl = 0.0 if abs(den) < 1e-12 else float(np.clip(0.5 * (y0 - y2) / den, -1.0, 1.0))
    else:
        dl = 0.0
    step = LOG_GRID[1] - LOG_GRID[0]
    f0 = float(np.exp(LOG_GRID[i] + dl * step))
    margin = min(np.log(f0 / win[0]), np.log(win[1] / f0)) / np.log(win[1] / win[0])
    return {"f0": f0, "value": float(d[i]), "prom": prom, "edge": bool(at_edge),
            "margin_frac": float(margin)}


def floor_db(f, mag_db, lo=5.0, hi=15.0):
    """Deconvolution-residual level below the sweep's own 20 Hz start.  DIAGNOSTIC ONLY.

    ⚠⚠ THIS IS NOT USED AS AN EXCLUSION, AND THE FIRST VERSION OF THIS GATE USED IT AS ONE --
    re-committing a mistake GATE R has already documented and paid for.  The sub-20 Hz residue is
    signal-PROPORTIONAL regularisation residue (GATE R measured it tracking the stimulus almost
    1:1, -35.4 -> -15.1 dB across the ladder), so gating on it deletes exactly the deep-notch cells
    a notch audit exists to measure: here it refused 480 readings, including every LF cell of the
    dose-response that carries W4's finding.  There IS no noise floor -- both sides are
    deterministic renders (ND's own five takes agree to -147..-164 dBFS).

    It is still worth PRINTING: a notch bottom at or below the residue means the DEPTH is not
    resolved.  This gate measures CENTRES, which are set by a feature's flanks and remain well
    determined when its bottom is not -- so the honest handling is to report the depth as
    unresolved and keep the centre, which is what W3 now does."""
    m = (f >= lo) & (f <= hi)
    return float(np.median(mag_db[m])) if m.any() else -np.inf


def features_of(al, sw, ref):
    """Locate every named feature on one side of one (capture, sweep) cell."""
    f, m = A.transfer_h1(A.seg_of(al, sw), ref)
    d = smooth(f, m)
    fl = floor_db(f, m)
    out = {"floor_db": fl, "peak_db": float(np.max(d))}
    for name, kind, win, _ in FEATURES:
        r = locate(d, win, kind)
        r["floor_margin_db"] = r["value"] - fl
        out[name] = r
    return out


# ---- one capture -------------------------------------------------------------------------------
def _cell(args):
    fname, ren_dir, extra = args
    orig, ref = _load_orig()
    parsed = C.parse_capture(fname)
    ra = C.render_args(parsed)
    tag = fname.replace(".wav", "")
    if extra:
        for k, v in extra:
            if k in ra:
                ra[ra.index(k) + 1] = v
            else:
                ra += [k, v]
        tag += "__" + "_".join(f"{k.lstrip('-')}{v}" for k, v in extra).replace(".", "p")
    out = os.path.join(ren_dir, tag + "_plugin.wav")
    render(out, ra)
    cap_al, _ = A.align(C.load_capture(os.path.join(C.CAPTURE_DIR, fname)), orig)
    ren_al, _ = A.align(A.load(out), orig)
    rec = {"file": fname, "settings": parsed, "model": {}, "pedal": {}}
    for sw in SWEEPS:
        rec["model"][sw] = features_of(ren_al, sw, ref)
        rec["pedal"][sw] = features_of(cap_al, sw, ref)
    return rec


def collect(files, ren_dir=REN_DIR, extra=None, jobs=None):
    return pmap(_cell, [(f, ren_dir, extra or []) for f in files], jobs=jobs)


# ================================ THE GATES =====================================================
def gate_w1(out, jobs):
    """KNOWN ANSWERS for the locator: GATE R's stored frequencies, and the R-C scaling law."""
    print("\n" + "=" * 92)
    print("W1  KNOWN ANSWERS -- the locator, before anything is read off it")
    print("=" * 92)
    if not os.path.exists(GATE_R_REPORT):
        sys.exit(f"GATE W1: {GATE_R_REPORT} is absent -- GATE R must have been run, or W1 has "
                 f"nothing to reproduce against and every number below is unvalidated")
    R = json.load(open(GATE_R_REPORT))
    want_mid = R["r2"]["shipped_hz"]
    want_bt = R["r1"]["bt_base_hz"]

    base = collect([GATE_R_ARM_CAP], ARM_DIR, [], jobs)[0]
    best = GATE_R_SWEEP          # NAMED -- see the constant.  Never selected by agreement.
    got_mid = base["model"][best]["mid_notch"]["f0"]
    got_bt = base["model"][best]["bt_notch"]["f0"]
    e_mid = abs(got_mid - want_mid) / want_mid
    e_bt = abs(got_bt - want_bt) / want_bt
    print(f"  (a) vs GATE R ({GATE_R_ARM_CAP}, {best}) -- two estimators, no shared arithmetic:")
    print(f"      mid notch : GATE R {want_mid:8.2f} Hz | GATE W {got_mid:8.2f} Hz "
          f"| {e_mid*100:5.2f} %   {'OK' if e_mid <= KA_TOL_FRAC else 'FAIL'}")
    print(f"      bridged-T : GATE R {want_bt:8.2f} Hz | GATE W {got_bt:8.2f} Hz "
          f"| {e_bt*100:5.2f} %   {'OK' if e_bt <= KA_TOL_FRAC else 'FAIL'}")
    if max(e_mid, e_bt) > KA_TOL_FRAC:
        sys.exit(f"GATE W1a: the locator does NOT reproduce GATE R's notch frequencies "
                 f"(worst {max(e_mid, e_bt)*100:.2f} % > {KA_TOL_FRAC*100:.0f} %) -- it is either "
                 f"tracking a different feature or the smoothing is biasing the vertex")

    # (b) THE PHYSICS.  Both networks are R-C, so scaling ONE network's caps by k moves ITS OWN
    # notch by exactly 1/k and leaves the other alone.  This is what makes (a) non-vacuous: (a)
    # alone would also pass for an estimator that happens to agree at one operating point.
    orig, ref = _load_orig()
    ap = C.render_args(C.parse_capture(GATE_R_ARM_CAP))
    for k, v in SHIP_LADDER.items():
        ap += ["--fit", f"{k}={v * 2.0:.6e}"]
    aout = render(os.path.join(ARM_DIR, "ladder_x2.wav"), ap)
    al, _ = A.align(A.load(aout), orig)
    f, m = A.transfer_h1(A.seg_of(al, best), ref)
    d = smooth(f, m)
    a_mid = locate(d, MID_WIN_MOVED, "min")
    a_bt = locate(d, FEAT_BY_NAME["bt_notch"][2], "min")
    ratio = got_mid / a_mid["f0"]
    bt_move = abs(a_bt["f0"] - got_bt) / got_bt
    print(f"  (b) ladder caps x2 -- the mid notch MUST halve, the bridged-T MUST NOT move:")
    print(f"      mid notch : {got_mid:8.2f} -> {a_mid['f0']:8.2f} Hz | ratio {ratio:.4f} vs "
          f"2.0000 | {'OK' if abs(ratio-2.0) <= SCALE_TOL*2 else 'FAIL'}"
          f"   (moved-window {MID_WIN_MOVED[0]:.0f}-{MID_WIN_MOVED[1]:.0f} Hz, "
          f"prominence {a_mid['prom']:.2f} dB, margin {a_mid['margin_frac']:.3f})")
    print(f"      bridged-T : {got_bt:8.2f} -> {a_bt['f0']:8.2f} Hz | moved {bt_move*100:5.2f} % "
          f"| {'OK' if bt_move <= STATIC_TOL_FRAC else 'FAIL'}")
    # A perturbation arm gets the SAME validity guards as the data -- `locate` always returns
    # something, so an unguarded arm reading is how a window defect reads as a physics failure.
    for tag, v in (("moved mid notch", a_mid), ("bridged-T", a_bt)):
        if v["edge"] or v["margin_frac"] < EDGE_MARGIN_FRAC or v["prom"] < MIN_PROM_DB:
            sys.exit(f"GATE W1b: the arm's {tag} is not a valid reading (edge={v['edge']}, "
                     f"margin={v['margin_frac']:.3f}, prominence={v['prom']:.2f} dB) -- fix the "
                     f"window before reading the ratio, do not loosen the ratio")
    if abs(ratio - 2.0) > SCALE_TOL * 2 or bt_move > STATIC_TOL_FRAC:
        sys.exit("GATE W1b: the locator does not follow the R-C scaling law -- it is not tracking "
                 "the network it names, so no centre frequency below can be quoted")
    # What the locator actually RESOLVES, measured rather than asserted.
    print(f"  grid cell {GRID_STEP_FRAC*100:.2f} %; the two known answers agree to "
          f"{max(e_mid, e_bt)*100:.2f} % -> quote no ratio finer than ~{max(e_mid,e_bt)*100:.1f} %")
    out["w1"] = {"gate_r_mid": want_mid, "got_mid": got_mid, "gate_r_bt": want_bt, "got_bt": got_bt,
                 "err_mid_frac": e_mid, "err_bt_frac": e_bt, "scale_ratio": ratio,
                 "bt_move_frac": bt_move, "sweep": best, "resolution_frac": max(e_mid, e_bt)}
    return max(e_mid, e_bt)


REF_OD = "ref-od.wav"


def level_ladder(caps):
    """The LEVEL ladder, resolved by SETTINGS not by filename.

    LEVEL noon is `ref-od.wav` -- there is no `level-1200_base-od.wav` -- so a name transform can
    only ever see part of this ladder (s112's twin-resolution lesson, in its other direction).

    ⚠ The reference condition is READ from `ref-od.wav`'s own stored settings, never typed.  A
    first draft hardcoded `attackIdx == 1` from a record I had glanced at; the matrix default is
    **0**, so the filter silently selected the two `attack-boost` captures instead of the ladder
    and W2 refused with "only 2 detents".  `rebuild-targets-dont-transcribe`, and the reason W2
    asserts a COUNT rather than trusting whatever the filter returns."""
    if REF_OD not in caps:
        sys.exit(f"GATE W2: {REF_OD} is absent from the report -- it defines the ladder's own "
                 f"reference condition, so nothing below can be selected")
    ref = dict(caps[REF_OD]["settings"])
    ref.pop("level", None)
    lad = {}
    for f, c in caps.items():
        s = dict(c.get("settings", {}))
        if not MG.is_od(f) or Q.DEFECT_TOKEN in f:
            continue
        s.pop("level", None)
        if s != ref:
            continue
        lad.setdefault(caps[f]["settings"]["level"], []).append(f)
    dupes = {k: v for k, v in lad.items() if len(v) > 1}
    if dupes:
        sys.exit(f"GATE W2: duplicate captures at one LEVEL detent {dupes} -- which one represents "
                 f"the detent is a real choice and must be made explicitly, not by dict order")
    return {k: v[0] for k, v in sorted(lad.items())}


def gate_w2(caps, out, jobs):
    """MEMBERSHIP, asserted."""
    print("\n" + "=" * 92)
    print("W2  MEMBERSHIP -- asserted, never inferred")
    print("=" * 92)
    lad = level_ladder(caps)
    eps = Q.endpoints_od(caps)
    print(f"  LEVEL ladder      : {len(lad)} detents  {sorted(lad)}")
    for lv, f in lad.items():
        print(f"      LEVEL {lv:<6.3f} {f}")
    if len(lad) < 6:
        sys.exit(f"GATE W2: the LEVEL ladder has only {len(lad)} detents -- W4's dose-response "
                 f"needs the ladder, and a short one is a membership defect, not a weak result")
    n12 = [f for f in eps if MG.is_gain_n12(f)]
    print(f"  pure-OD endpoints : {len(eps)} (GATE Q's own selection, "
          f"expected {R.EXPECT_ENDPOINTS})")
    print(f"      of which `gain-n12` (a SECOND operating point -- s108 P4): {len(n12)} {n12}")
    if len(eps) != R.EXPECT_ENDPOINTS:
        sys.exit(f"GATE W2: GATE Q's endpoint count moved ({len(eps)} vs {R.EXPECT_ENDPOINTS}) -- "
                 f"bump it there DELIBERATELY after checking what arrived")
    if Q.DEFECT_TOKEN not in "".join(caps):
        sys.exit(f"GATE W2: the `{Q.DEFECT_TOKEN}` token matched NOTHING -- an exclusion that "
                 f"excludes nothing is `empty-gate-must-fail` in a costume")
    out["w2"] = {"ladder": {str(k): v for k, v in lad.items()}, "endpoints": eps, "n12": n12}
    return lad, [e for e in eps if not MG.is_gain_n12(e)]


def gate_w3(rows, out):
    """WINDOW VALIDITY: nothing may rest on an edge, and the floor margin is printed."""
    print("\n" + "=" * 92)
    print("W3  WINDOW VALIDITY -- a bound is not a measurement")
    print("=" * 92)
    worst = {}
    edges = []
    floors = []
    faint = []
    proms = []
    for r in rows:
        for side in ("model", "pedal"):
            for sw in SWEEPS:
                cell = r[side][sw]
                for name, kind, win, _ in FEATURES:
                    v = cell[name]
                    key = (name, side)
                    worst[key] = min(worst.get(key, 1.0), v["margin_frac"])
                    proms.append(v["prom"])
                    if v["edge"] or v["margin_frac"] < EDGE_MARGIN_FRAC:
                        edges.append((name, side, r["file"], sw, v["f0"]))
                    if v["floor_margin_db"] < 6.0:
                        floors.append((name, side, r["file"], sw, v["floor_margin_db"]))
                    if v["prom"] < MIN_PROM_DB:
                        faint.append((name, side, r["file"], sw, v["prom"]))
    pa = np.array(proms)
    counts = [(b, int((pa < b).sum())) for b in PROM_SWEEP]
    print(f"  prominence over all {len(pa)} readings: "
          f"p10 {np.percentile(pa,10):.2f} / median {np.median(pa):.2f} / "
          f"p90 {np.percentile(pa,90):.2f} dB")
    print(f"  excluded-as-faint at each bar: " +
          "  ".join(f"{b:.1f} dB -> {c}" for b, c in counts) +
          f"   (shipped bar {MIN_PROM_DB:.1f} dB)")
    if len({c for _, c in counts}) == 1:
        sys.exit("GATE W3: the prominence bar excludes the SAME count at every setting -- the knob "
                 "is not turning, so this sweep is a constant printed four times, not a robustness "
                 "check (s106 N5)")
    print(f"  {'feature':<14s} {'window Hz':>16s}   worst margin (model / pedal), "
          f"fraction of the window in log-f")
    for name, kind, win, _ in FEATURES:
        print(f"  {name:<14s} {win[0]:7.0f}-{win[1]:<8.0f} "
              f"{worst.get((name,'model'),float('nan')):6.3f} / "
              f"{worst.get((name,'pedal'),float('nan')):6.3f}")
    print(f"  REFUSED readings -- edge-resting {len(edges)} | too faint to be a feature "
          f"{len(faint)}")
    print(f"  REPORTED, NOT refused -- notch bottom at/below the sub-20 Hz deconvolution residue: "
          f"{len(floors)} (the DEPTH is unresolved there; the CENTRE is set by the flanks and is "
          f"kept -- see floor_db)")
    for e in edges[:6]:
        print(f"      EDGE  {e[0]:<13s} {e[1]:<6s} {e[2]:<48s} {e[3]:<14s} {e[4]:8.1f} Hz")
    for e in floors[:4]:
        print(f"      FLOOR {e[0]:<13s} {e[1]:<6s} {e[2]:<48s} {e[3]:<14s} {e[4]:+6.2f} dB")
    for e in faint[:6]:
        print(f"      FAINT {e[0]:<13s} {e[1]:<6s} {e[2]:<48s} {e[3]:<14s} {e[4]:6.2f} dB")
    out["w3"] = {"edges": len(edges), "floors": len(floors), "faint": len(faint),
                 "prom_counts": counts,
                 "worst_margin": {f"{k[0]}|{k[1]}": v for k, v in worst.items()},
                 "edge_rows": edges[:40], "floor_rows": floors[:40], "faint_rows": faint[:40]}
    return (set((e[0], e[1], e[2], e[3]) for e in edges)
            | set((f[0], f[1], f[2], f[3]) for f in faint))


def gate_w4(lad, rows, bad, out, resolution):
    """THE DISCRIMINATOR: does the feature's CENTRE move with LEVEL?

    LEVEL is downstream of every filter in the chain, so a NETWORK corner cannot move with it at
    all.  A MIX cancellation must: its centre is set by where the two summed paths are
    equal-and-opposite, and LEVEL changes that balance (GATE K2 -- the clean coefficient runs from
    -0.08 dB re the OD at LEVEL 0.125 to exactly zero at LEVEL max).

    ⚠ The bar is placed against the locator's OWN measured resolution (W1), not chosen:
    `measure-the-distribution-before-placing-a-threshold`."""
    print("\n" + "=" * 92)
    print("W4  THE DISCRIMINATOR -- LEVEL dose-response.  MIX cancellation or NETWORK corner?")
    print("=" * 92)
    bar = max(MIX_MOVE_FRAC, 3.0 * resolution)
    print(f"  read at {SWEEPS[0]} ONLY -- the quietest stimulus, so LEVEL is varied with drive as "
          f"close to out of the picture as the capture set allows.  W6 varies drive separately.")
    print(f"  bar: a centre must move by > {bar*100:.1f} % across the ladder to read as MIX "
          f"(3x the locator's measured {resolution*100:.2f} % agreement, floored at "
          f"{MIX_MOVE_FRAC*100:.0f} %)")
    by_file = {r["file"]: r for r in rows}
    levels = sorted(lad)
    sw = SWEEPS[0]
    res = {}
    print(f"\n  {'feature':<14s} {'side':<6s} " +
          " ".join(f"{lv:>7.3f}" for lv in levels) + "   span    verdict")
    for name, kind, win, label in FEATURES:
        res[name] = {}
        for side in ("model", "pedal"):
            fs, shown = [], []
            for lv in levels:
                f = lad[lv]
                r = by_file.get(f)
                if r is None or (name, side, f, sw) in bad:
                    shown.append("      -")
                    continue
                v = r[side][sw][name]["f0"]
                fs.append(v)
                shown.append(f"{v:7.1f}")
            span = (max(fs) / min(fs) - 1.0) if len(fs) >= 3 else float("nan")
            verdict = ("UNRESOLVED" if not np.isfinite(span)
                       else "MIX" if span > bar else "NETWORK")
            res[name][side] = {"f0": fs, "span_frac": span, "verdict": verdict}
            print(f"  {name:<14s} {side:<6s} " + " ".join(shown) +
                  ("     nan " if not np.isfinite(span) else f"  {span*100:5.1f}%") +
                  f"   {verdict}")
        both = {res[name][s]["verdict"] for s in ("model", "pedal")}
        agree = "both" if len(both) == 1 else "DISAGREE"
        res[name]["agreement"] = agree
        print(f"  {'':<14s} {'':<6s} -> {label}: {agree} {'/'.join(sorted(both))}")
    out["w4"] = res
    return res


def gate_w5(eps, rows, bad, out, w4, resolution):
    """THE BLEED-FREE OD-PATH READ -- the audit's actual answer.

    At BLEND = LEVEL = 1 the mix coefficient is exactly 1 and the clean tap exactly 0 (GATE K2's
    two exact zeros), so every feature here belongs to the OD path alone and a centre ratio is a
    statement about a network, not about a balance."""
    print("\n" + "=" * 92)
    print("W5  THE BLEED-FREE OD PATH (BLEND = LEVEL = 1) -- model vs ND capture, centre ratios")
    print("=" * 92)
    by_file = {r["file"]: r for r in rows}
    res = {}
    print(f"  n = {len(eps)} pure-OD endpoints x {len(SWEEPS)} stimulus levels.  "
          f"Per-condition spread PRINTED (s108 P4 -- a pooled centre with no spread is not a "
          f"measurement).")
    print(f"\n  {'feature':<14s} {'model Hz':>18s} {'pedal Hz':>18s}   "
          f"{'model/pedal':>11s}   n   W4")
    for name, kind, win, label in FEATURES:
        mm, pp, rr = [], [], []
        for f in eps:
            r = by_file.get(f)
            if r is None:
                continue
            for sw in SWEEPS:
                if (name, "model", f, sw) in bad or (name, "pedal", f, sw) in bad:
                    continue
                a, b = r["model"][sw][name]["f0"], r["pedal"][sw][name]["f0"]
                mm.append(a)
                pp.append(b)
                # ⚠ PAIRED.  A ratio of two POOLED medians is not the same statistic as the median
                # of the paired ratios, and the two diverge exactly when the quantity varies across
                # conditions -- which several of these features do by up to 35 %.  The pair shares
                # its condition, so every nuisance (drive, switches, stimulus) cancels inside it.
                rr.append(a / b)
        if len(rr) < 4:
            print(f"  {name:<14s} {'--':>18s} {'--':>18s}   {'--':>11s}  {len(rr):3d}   "
                  f"(too few valid readings)")
            res[name] = {"n": len(rr), "verdict": "NO DATA"}
            continue
        ra = np.array(rr)
        ratio = float(np.median(ra))
        iqr = float(np.percentile(ra, 75) - np.percentile(ra, 25))
        spread_m = (max(mm) / min(mm) - 1.0)
        spread_p = (max(pp) / min(pp) - 1.0)
        v4 = w4.get(name, {}).get("agreement", "?")
        # A gap is only resolved while it is larger than the scatter of the very ratios it pools:
        # `check-n-before-reading-a-trend` applied to a spread rather than a count.
        big = abs(ratio - 1.0) > max(3.0 * resolution, 0.02)
        resolved = abs(ratio - 1.0) > iqr
        sig = bool(big and resolved)
        res[name] = {"n": len(rr), "model_hz": float(np.median(mm)),
                     "pedal_hz": float(np.median(pp)), "ratio": ratio, "ratio_iqr": iqr,
                     "spread_model_frac": spread_m, "spread_pedal_frac": spread_p,
                     "significant": sig, "resolved": bool(resolved)}
        tag = ("   <-- MISMATCH" if sig else
               "   (gap < its own IQR: NOT RESOLVED)" if big else "")
        print(f"  {name:<14s} {np.median(mm):9.1f} +-{spread_m*100:5.1f}% "
              f"{np.median(pp):9.1f} +-{spread_p*100:5.1f}%   "
              f"{ratio:7.3f}x+-{iqr:.3f}  {len(rr):3d}   {v4}{tag}")
    out["w5"] = res
    return res


def gate_w5b(lad, rows, bad, out, resolution):
    """MATCHED-LEVEL ladder ratio -- the read W5 structurally cannot make.

    W5 is bleed-free, so a feature that EXISTS ONLY IN THE MIX (the bass notch is exactly this:
    it is a cancellation between the OD path and the clean tap, so it vanishes at LEVEL max where
    the clean coefficient is exactly zero) has no bleed-free reading and W5 can only say
    "unmeasured".  That is honest and useless.  The ladder does measure it: at each detent both
    sides are at the SAME nominal mix, so the model/pedal ratio there is a matched comparison.

    ⚠ "Same nominal mix" is not "same actual mix" -- the two sides' OD/clean BALANCE differs by
    A3, which is the whole point.  So this ratio is not a corner error even when it is large and
    stable; it is the balance error expressed as a frequency.  W7 says so rather than promoting it."""
    print("\n" + "=" * 92)
    print("W5b MATCHED-LEVEL LADDER -- for features that exist only in the MIX, so W5 cannot see them")
    print("=" * 92)
    by_file = {r["file"]: r for r in rows}
    sw = SWEEPS[0]
    res = {}
    print(f"  read at {SWEEPS[0]} ONLY (as W4).  PAIRED per detent, then pooled -- never a ratio "
          f"of two pooled medians.")
    print(f"  {'feature':<14s} {'detents':>8s}  {'model/pedal (median +- IQR)':>28s}   per-detent ratios")
    for name, kind, win, label in FEATURES:
        rr, shown = [], []
        for lv in sorted(lad):
            f = lad[lv]
            r = by_file.get(f)
            if r is None or (name, "model", f, sw) in bad or (name, "pedal", f, sw) in bad:
                continue
            q = r["model"][sw][name]["f0"] / r["pedal"][sw][name]["f0"]
            rr.append(q)
            shown.append(f"{lv:.3f}:{q:.3f}")
        if len(rr) < 3:
            print(f"  {name:<14s} {len(rr):8d}  {'--':>28s}")
            res[name] = {"n": len(rr), "verdict": "NO DATA"}
            continue
        ra = np.array(rr)
        med = float(np.median(ra))
        iqr = float(np.percentile(ra, 75) - np.percentile(ra, 25))
        stable = iqr < max(3.0 * resolution, 0.02)
        res[name] = {"n": len(rr), "ratio": med, "ratio_iqr": iqr, "stable": bool(stable),
                     "per_detent": shown}
        print(f"  {name:<14s} {len(rr):8d}  {med:19.3f}x +-{iqr:.3f}   " + "  ".join(shown[:5]))
        print(f"  {'':<14s} {'':>8s}  {'':>28s}   "
              + ("ratio is STABLE across the ladder" if stable else
                 "ratio MOVES with LEVEL -- the two sides' mix behaves differently"))
    out["w5b"] = res
    return res


def gate_w6(eps, rows, bad, out):
    """STIMULUS DEPENDENCE.  A fixed linear network's centre cannot depend on drive level."""
    print("\n" + "=" * 92)
    print("W6  STIMULUS DEPENDENCE -- a fixed network's centre CANNOT move with drive")
    print("=" * 92)
    by_file = {r["file"]: r for r in rows}
    res = {}
    print(f"  {'feature':<14s} {'side':<6s} " + " ".join(f"{s.replace('sweep_',''):>10s}"
                                                         for s in SWEEPS) + "    span")
    for name, kind, win, label in FEATURES:
        res[name] = {}
        for side in ("model", "pedal"):
            meds = []
            cells = []
            for sw in SWEEPS:
                vals = [by_file[f][side][sw][name]["f0"] for f in eps
                        if f in by_file and (name, side, f, sw) not in bad]
                if not vals:
                    cells.append("         -")
                    continue
                meds.append(float(np.median(vals)))
                cells.append(f"{np.median(vals):10.1f}")
            span = (max(meds) / min(meds) - 1.0) if len(meds) >= 3 else float("nan")
            res[name][side] = {"medians": meds, "span_frac": span,
                               "verdict": ("UNRESOLVED" if not np.isfinite(span) else
                                           "DRIVE-DEPENDENT" if span > STIM_MOVE_FRAC else "FIXED")}
            print(f"  {name:<14s} {side:<6s} " + " ".join(cells) +
                  ("     nan" if not np.isfinite(span) else f"  {span*100:6.1f}%") +
                  f"  {res[name][side]['verdict']}")
    out["w6"] = res
    return res


def gate_w7(w4, w5, w5b, w6, out):
    """THE HW-vs-ND CLASSIFICATION the session-119 item asked for, applied to survivors."""
    print("\n" + "=" * 92)
    print("W7  CLASSIFICATION -- what each mismatch IS, before anything is called a model defect")
    print("=" * 92)
    print("  (a) a fixed-network CORNER error in the model      -> an element/value target")
    print("  (b) a MIX / BALANCE property (A3 seen as a centre) -> NOT a corner; do not point an")
    print("      optimiser at a capacitor for it")
    print("  (c) NOT A FIXED-NETWORK FEATURE on at least one side -- its centre moves with drive,")
    print("      which no fixed linear network's can.  Where that side is the PEDAL and the region")
    print("      is HF, this is reference-sources.md / GATE I territory and ND is not authoritative.")
    res = {}
    for name, kind, win, label in FEATURES:
        v5 = w5.get(name, {})
        v5b = w5b.get(name, {})
        mix_model = w4.get(name, {}).get("model", {}).get("verdict", "?")
        mix_pedal = w4.get(name, {}).get("pedal", {}).get("verdict", "?")
        drv = {s: w6.get(name, {}).get(s, {}).get("verdict", "?") for s in ("model", "pedal")}
        notes = []
        # ⚠ W6's drive test only bears on COMPARABILITY where both sides actually have a
        # bleed-free reading.  For a feature the model does not have bleed-free at all, the
        # pedal's drive-dependence there says nothing about the comparison being made (which is
        # the ladder's), so it must not outrank the MIX verdict.
        comparable = v5.get("n", 0) >= 4
        if v5b.get("n", 0) >= 3:
            notes.append(f"matched-LEVEL model/pedal ratio {v5b['ratio']:.3f}x "
                         f"+-{v5b['ratio_iqr']:.3f} over {v5b['n']} detents")
        if comparable and drv["model"] != drv["pedal"] and "UNRESOLVED" not in drv.values():
            fixed = "model" if drv["model"] == "FIXED" else "pedal"
            other = "pedal" if fixed == "model" else "model"
            cls = "(c) NOT THE SAME KIND OF FEATURE"
            why = (f"the {fixed}'s centre is FIXED across the 24 dB stimulus ladder and the "
                   f"{other}'s MOVES ({w6[name][other]['span_frac']*100:.1f} %).  A fixed linear "
                   f"network's centre cannot move with drive, so one of these is a network and the "
                   f"other is drive-generated -- their centres are not the same quantity and the "
                   f"{v5['ratio']:.3f}x 'gap' is not a corner error")
        elif comparable and all(v == "DRIVE-DEPENDENT" for v in drv.values()):
            cls = "(c) NOT A FIXED NETWORK, EITHER SIDE"
            why = (f"both centres move with drive (model {w6[name]['model']['span_frac']*100:.1f} %, "
                   f"pedal {w6[name]['pedal']['span_frac']*100:.1f} %) -- this is not a corner on "
                   f"either side, so a {v5['ratio']:.3f}x ratio is not an element target")
        elif mix_model == "MIX" or mix_pedal == "MIX":
            cls = "(b) MIX / BALANCE"
            why = (f"the centre MOVES with LEVEL (model {mix_model}, pedal {mix_pedal}) -- LEVEL "
                   f"sits downstream of every filter, so no corner can do that")
            if v5.get("verdict") == "NO DATA":
                why += "; and the feature VANISHES bleed-free, which is a cancellation's signature"
            if v5.get("significant"):
                cls += " + BLEED-FREE RESIDUAL"
                why += f"; and a {v5['ratio']:.3f}x gap SURVIVES bleed-free"
            if drv["pedal"] == "DRIVE-DEPENDENT":
                notes.append(f"the PEDAL's centre also moves {w6[name]['pedal']['span_frac']*100:.1f} % "
                             f"with drive -- drive-generated on the reference side")
        elif not comparable:
            cls, why = "(unmeasured)", "no valid bleed-free reading and no ladder reading"
        elif v5.get("significant"):
            cls = "(a) OD-PATH CORNER ERROR"
            why = (f"{v5['ratio']:.3f}x +-{v5['ratio_iqr']:.3f}, bleed-free, and FIXED across drive "
                   f"on both sides -- a located element/value target")
        elif abs(v5.get("ratio", 1.0) - 1.0) > 0.02:
            cls, why = "UNRESOLVED", (f"{v5['ratio']:.3f}x but its own IQR is "
                                      f"{v5['ratio_iqr']:.3f} -- the gap is inside the scatter")
        else:
            cls, why = "MATCHES", (f"{v5['ratio']:.3f}x +-{v5['ratio_iqr']:.3f} bleed-free, and "
                                   f"FIXED across drive on both sides")
        res[name] = {"class": cls, "why": why, "notes": notes}
        print(f"\n  {name:<14s} {label}")
        print(f"      {cls}")
        print(f"      {why}")
        for n in notes:
            print(f"      + {n}")
    out["w7"] = res
    return res


def main():
    ap = argparse.ArgumentParser(description="GATE W -- peak/notch centre-frequency audit")
    ap.add_argument("--report", default=REPORT)
    ap.add_argument("--jobs", type=int, default=None)
    # ⚠ There is deliberately NO `--full` flag.  An earlier draft parsed one and did nothing with
    # it, which is exactly the kind of dead control a later session reads as coverage it does not
    # have.  Extending to all ~105 OD captures is a ~20 min render and would tighten the spreads;
    # it would change no verdict here, because every verdict rests on a dose-response rather than
    # on a pooled mean.
    ap.add_argument("--json", default=OUT_JSON)
    args = ap.parse_args()

    if not os.path.exists(args.report):
        sys.exit(f"GATE W: {args.report} not found")
    rep = json.load(open(args.report))
    caps = {c["file"]: c for c in rep["captures"]}
    out = {"report": args.report, "features": [list(f) for f in FEATURES],
           "grid_frac": GRID_FRAC}

    print("=" * 92)
    print(f"GATE W -- peak/notch CENTRE-frequency audit   (report: {args.report})")
    print("=" * 92)

    resolution = gate_w1(out, args.jobs)
    lad, eps = gate_w2(caps, out, args.jobs)

    files = sorted(set(list(lad.values()) + eps))
    print(f"\n  rendering / reading {len(files)} captures x {len(SWEEPS)} sweeps ...")
    rows = collect(files, REN_DIR, [], args.jobs)

    # LEVEL min: the model MUTES (GATE L7).  MEASURED, not assumed.
    drop_files = []
    for r in rows:
        pk = max(r["model"][s]["peak_db"] for s in SWEEPS)
        if pk < SILENT_DB:
            drop_files.append((r["file"], pk))
    if drop_files:
        print(f"  model SILENT (GATE L7's LEVEL-min mute), excluded and measured: " +
              ", ".join(f"{f} (peak {p:.0f} dB)" for f, p in drop_files))
    silent = {f for f, _ in drop_files}
    rows = [r for r in rows if r["file"] not in silent]
    lad = {k: v for k, v in lad.items() if v not in silent}
    eps = [e for e in eps if e not in silent]

    bad = gate_w3(rows, out)
    w4 = gate_w4(lad, rows, bad, out, resolution)
    w5 = gate_w5(eps, rows, bad, out, w4, resolution)
    w5b = gate_w5b(lad, rows, bad, out, resolution)
    w6 = gate_w6(eps, rows, bad, out)
    w7 = gate_w7(w4, w5, w5b, w6, out)

    os.makedirs(os.path.dirname(args.json), exist_ok=True)
    with open(args.json, "w") as fh:
        json.dump(out, fh, indent=1)
    print(f"\n  -> {args.json}")

    fails = [n for n, v in w7.items() if v["class"].startswith("(a)")]
    print("\n" + "=" * 92)
    if fails:
        print(f"GATE W: {len(fails)} OD-PATH centre mismatch(es) survive every discriminator: "
              f"{', '.join(fails)}")
    else:
        print("GATE W: no OD-path centre mismatch survives the discriminators")
    print("=" * 92)
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
