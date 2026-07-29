#!/usr/bin/env python3.11
"""Can the two-pole ATTACK topology be made to match the null's WIDTH as well as its (f0, depth)?
Session 64, Phase 9 / A3 step 21 -- session 63's next-step (a).

THE QUESTION
------------
Session 63 built the two-pole topology and it met the notch requirement TO THE BIN at all three
throws (f0 316.4 / 328.1 / 334.0 Hz, spread 17.58 Hz) and the broadband gain at the quiet end
(+8.28 vs +8.91 dB boost, -2.29 vs -2.38 cut). What it did NOT meet is the SHAPE:

  * every null is ~2x too BROAD -- half-depth width (interpolated) 150.6 / 59.6 / 138.6 Hz against
    the pedal's 77.9 / 27.1 / 71.9 (cut / boost / flat), i.e. 1.93 / 2.20 / 1.93;
  * the broadband slope has the WRONG SIGN on both throws (boost -1.39 dB/dec vs the pedal's +1.23,
    cut +0.10 vs -1.38).

⭐ The width excess is a nearly UNIFORM factor across all three throws, and the throws differ only
in pole B (Rd, C5). A per-throw element cannot produce a uniform error; a SHARED one can. So session
63's next step was named as a SHARED-element fit -- the ladder RC / R12 / R14 -- not a switch fit.
This tool tests that, and it tests it in the order that can produce a NEGATIVE result: census
first, then the SMALLEST structure that could work, then larger ones.

⛔ AND IT IS BUILT TO BE ABLE TO REFUTE, WHICH IS THE POINT. 12 free values against 9 notch numbers
hit them by construction (session 61 item 10b's own warning, and session 62 item 4's control where
adding R12 to the switched set reached notch cost 0.000 via broadband nonsense). So the families are
tried in increasing size and the FIRST one that works is the claim -- an over-parameterised success
is reported as such and is not evidence.

⚠⚠ THE CALIBRATION, WHICH IS THIS SESSION'S LOAD-BEARING METHOD FINDING
----------------------------------------------------------------------
The fast network solve is NOT interchangeable with the shipped chain on the quantities being fitted
here, and every ATTACK screen since session 61 has implicitly assumed it is:

    at session 62's own proposal point, treble-ladder-only vs the REAL RENDER --
      f0     316.25 / 327.75 / 333.75   vs   316.4 / 328.1 / 334.0   -> agrees to 0.35 Hz
      depth   14.74 /  32.63 /  15.85   vs    18.51 / 36.62 / 20.31  -> the render is ~4 dB DEEPER
      width  121.3  /  52.3  / 139.6    vs   150.6 /  59.6 / 138.6   -> and up to 24 % wider

Cause, measured not guessed: `D(f) = render_dB - ladder_dB` is one shared downstream transfer to
within ~0.6 dB (six curves, two very different ladder settings x three throws) and it FALLS 17.1 dB
across 150-700 Hz -- the IC2_B bridged-T scoop heading for its 717 Hz minimum, plus the two
Sallen-Keys. Depth and width are both measured against a shoulder at 200-270 Hz, so that tilt is
inside them: it deepens the apparent null and drags its upper skirt out.

⇒ SESSION 62 FITTED DEPTH ON AN INSTRUMENT ~4 dB OFFSET FROM WHAT SHIPS. Its reported 0.18 dB worst
depth error was real in the ladder solve and became 3.6-4.3 dB through the chain -- which session 63
observed and (correctly, since depth is a lower bound) allowed, without noting that the two
instruments disagree. They do, and a width fit cannot survive a 24 % scale error, so the requirement
is transferred into the SCREEN'S OWN UNITS by a calibration measured at the proposal point:

    f0     passes straight through (0.35 Hz)
    depth  additive offset      (python = render + d)
    width  multiplicative       (python = render * k)

and the screen's verdict is then always re-checked on the REAL RENDER (`attack_render_gate.py`),
because a render is 17.6 s and an optimiser needs thousands of evaluations -- the screen FINDS the
lever, the render LANDS the value. GATE C below is that calibration's own out-of-sample test.

GATES -- none optional, all run before any number is read
--------------------------------------------------------
  A SOLVER      the collapsed/degenerate tap network must reproduce `eq_reference.treble_attack_tf`.
                Delegated to attack_tap_screen, whose gate already proves this to ~1e-14 dB -- not
                re-implemented here (one oracle, not a second copy: session 62's own rule).
  B WIDTH       `locate_notch`'s width must recover a SYNTHESISED notch of known width. A statistic
                nobody has checked cannot carry a 2x claim.
  C CALIBRATION out-of-sample and in BOTH directions between two different C8 = 0 ladders (see the
                ⚠⚠ note at CAL for why the DRAWN default cannot be the anchor). A calibration
                fitted and tested at the same point proves nothing (session 43's imposed-check
                lesson). ⚠ IT CHECKS, at +-5 Hz f0 / +-3.3 dB depth / +-10-27 % width -- so this
                screen is a LEVER FINDER and `attack_render_gate.py` is the arbiter. Stated by the
                tool rather than assumed away.
  D SEARCH      recover a target the family DEFINITIONALLY makes, so a large residual is readable as
                unreachability rather than a weak optimiser (sessions 57/58/61). ⚠ Scored on the
                NOTCH ONLY: a first draft left an unmatchable broadband term in the objective and
                the gate then failed on its own construction.
  E PATHOLOGY   inherited from attack_tap_screen.stats -- a dead or wildly-rippling response can
                fake an arbitrarily deep null (session 57 item 5).
  + BOX SWEEP   a large residual is only UNREACHABILITY if widening the search does not shrink it
                (session 57 item 4). ⚠ This is what stopped session 64 calling the width
                unreachable: at +-1 decade it looks like a hard conflict, and at +-3 decades the
                nine numbers are all met -- see `--best`.

SCOPE
-----
  ATTACK is [ENG] -- this proposes a topology and disagrees with no drawn circuit. Magnitude only.
  Notch depths are LOWER bounds (probe gate 1(b)), so the depth RANKING carries the claim. h is a
  ratio between throws, so anything common to all three cancels by construction.

WHAT IT FOUND (session 64) -- read this before re-running any of it
------------------------------------------------------------------
  * NO shared ladder element is a width lever: all of them move width and f0 TOGETHER at
    ~0.5-1.5 Hz per Hz, and f0 already matches to the bin. Only C7 is width-selective
    (11.4 Hz of width per Hz of f0) and its authority is small. The TAP divider is
    width-NEUTRAL (<=0.5 Hz) and f0-neutral (0.00 Hz), extending session 62's pole
    independence to the width statistic.
  * The nine notch numbers ARE reachable -- f0 to 0.25-1.0 Hz, width to 0.8-11.9 % -- but only
    at R7 x572 (200k -> 114 MOhm), C6 x62, C5/C9/C7 x0.02-0.03, with the tap on its bound and
    the broadband at 3.5x floor. That is session 62 item 4's "reachable via nonsense" control,
    not a candidate. ⇒ NOT a refutation (the box sweep forbids that reading) and NOT shippable.
  * ⭐⭐ AND THE BIGGER FINDING IS NOT ATTACK'S AT ALL -- see `--tilt`. The OD path's own
    absolute shape falls 11.05 dB over 200->480 Hz where the pedal falls 4.88, in ALL THREE
    throws, level-independent, and the IC2_B bridged-T accounts for 10.79 of those 11.05 dB.
    GAP #1b, reopened on an axis that can see it.
  * ⚠ The obvious mechanism -- "the excess tilt IS the width excess, both are ~2.1x" -- was
    TESTED AND REFUTED here: de-tilting moves the ratio only 1.93 -> 1.69. Coincidence.

Usage:
  python3.11 analysis/attack_shape_screen.py --render-cal    # once: the calibration anchor
  python3.11 analysis/attack_shape_screen.py --census        # the sensitivity table only
  python3.11 analysis/attack_shape_screen.py --tilt          # is the residual even ATTACK's?
  python3.11 analysis/attack_shape_screen.py --fit [--quick] [--json OUT]
  python3.11 analysis/attack_shape_screen.py --best [--json OUT]   # then:
  python3.11 analysis/attack_render_gate.py --both --fits-json <that JSON>
"""
import argparse
import io
import json
import os
import sys
from contextlib import redirect_stdout

import numpy as np
from scipy.optimize import differential_evolution

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import analyze as A                                       # noqa: E402
with redirect_stdout(io.StringIO()):
    import eq_reference as E                              # noqa: E402
    import attack_multipole_screen as M                   # noqa: E402  (solver-free: record, db)
    import attack_tap_screen as T                         # noqa: E402  (the PROVEN tap solver)
    import attack_notch_probe as P                        # noqa: E402  (locate_notch = one oracle)
    import attack_render_gate as RG                       # noqa: E402  (ONE render-condition source)

POSITIONS = P.POSITIONS                                   # cut, boost, flat
THROWS = ["boost", "cut"]
RENDER_DIR = "build/attack_render_gate"                   # attack_render_gate.py's own renders
CALDIR = "build/attack_shape_screen"

# ---- the reference ladder points ------------------------------------------------------------
PROP = dict(Ra=470.0e3, Rb=506.0e3, Rc=78.5e3, R11=212.0e3, R7=200e3, R12=6.8e3, R14=22e3,
            C5=19.7e-9, C9=22e-9, C6=22e-9, C7=680e-12)
PROP_RD = dict(boost=478.0, flat=6.14e3, cut=6.04e3)
PROP_C5T = dict(boost=1.1e-9, flat=0.0, cut=2.7e-9)

# ⚠⚠ THE CALIBRATION ANCHOR MUST HAVE C8 = 0, AND THE SHIPPED DEFAULT DOES NOT -- a first draft
# used the DRAWN default as the anchor and GATE C failed by 62 Hz of f0 at every throw, identically.
# That identical-across-throws error is the tell: `tf_tap` takes ONE optional `c8` spanning M<->T3,
# so it can express the drawn BOOST throw (C8 bridges R8) and cannot express CUT (C8 shunts P->GND)
# or FLAT (C8 open) at all. Passing c8 = 0 therefore models a drawn network with C8 REMOVED, which
# is a different circuit from the one that renders -- so the "calibration" was measuring a
# structural mismatch, not a downstream transfer. (The C++ stage hangs C8 off the SELECTED tap;
# attack_topology_goldens.py records that the two implementations disagree BY CONSTRUCTION when C8
# is in circuit, and that the proposal used neither.) The anchor below is therefore a genuinely
# DIFFERENT ladder at C8 = 0, where both implementations model the same network.
CAL = dict(PROP, R12=PROP["R12"] * 1.7, C9=PROP["C9"] * 0.6, C5=PROP["C5"] * 1.15)
CAL_RD = dict(PROP_RD, boost=700.0, flat=3.2e3)
CAL_C5T = dict(PROP_C5T)
CAL_FITS = ["attackTapRa=470e3", "attackTapRb=506e3", "attackTapRc=78.5e3", "attackTapR11=212e3",
            "trebleC5=%.6g" % CAL["C5"], "attackC5TrimBoost=1.1e-9", "attackC5TrimCut=2.7e-9",
            "trebleLadderDampR=3.2e3", "attackDampBoost=700", "attackDampCut=6.04e3",
            "trebleC8=0", "trebleLadderR12=%.6g" % CAL["R12"], "trebleC9=%.6g" % CAL["C9"]]

# ---- grids ---------------------------------------------------------------------------------
# The notch stats want resolution the 5.86 Hz measurement grid does not have (the pedal's boost
# null is 4 bins wide), so the SCREEN runs fine and the calibration carries the difference.
FNOTCH = np.arange(180.0, 500.01, 0.25)
ZNOTCH = E.jfet_source_z(FNOTCH, **M.ZS)
FBB = M.FBB                                               # the record's own broadband bins
ZBB = M.ZSA[-M.NBB:]
REC = M.REC
SEG = "sweep_clean"                                       # the -30 dBFS row the record quotes


# =============================================================================================
# statistics -- one definition, taken from locate_notch
# =============================================================================================
def notch_stats(mag):
    n = P.locate_notch(FNOTCH, mag)
    return n["f_bin"], n["depth"], n["width_i"]


ZNOTCH_OVERRIDE = None    # set only by scale_diagnostic(); None = the shipped J201 boundary


def solve(base, rd, c5t, pos, f, zs):
    p = dict(base)
    p["Rd"] = rd[pos]
    p["C5"] = base["C5"] + c5t[pos]
    if ZNOTCH_OVERRIDE is not None and len(f) == len(FNOTCH):
        zs = ZNOTCH_OVERRIDE
    return M.db(T.tf_tap(f, zs, T.TAP_OF[pos], p, 0.0))


def full_stats(base, rd, c5t):
    """(f0, depth, width) per throw + the broadband h curve and its shape descriptors."""
    out, hb = {}, {}
    for pos in POSITIONS:
        m = solve(base, rd, c5t, pos, FNOTCH, ZNOTCH)
        if not np.all(np.isfinite(m)):
            return None
        if m.max() < -160.0 or (m.max() - m.min()) > 80.0:        # GATE E PATHOLOGY
            return None
        out[pos] = notch_stats(m)
        hb[pos] = solve(base, rd, c5t, pos, FBB, ZBB)
    h = {q: hb[q] - hb["flat"] for q in THROWS}
    lg = np.log10(FBB)
    shape = {}
    for q in THROWS:
        c2, c1, _ = np.polyfit(lg, h[q], 2)
        shape[q] = (float(np.median(h[q])), float(c1 + 2.0 * c2 * float(np.mean(lg))))
    return dict(notch=out, h=h, shape=shape)


# =============================================================================================
# GATE B -- does the WIDTH statistic recover a known width?
# =============================================================================================
def gate_width():
    print("  B WIDTH       recover a SYNTHESISED notch of known half-depth width")
    print("      %8s %8s %10s %10s %9s" % ("f0 Hz", "depth", "true w", "recovered", "err %"))
    ok = True
    for f0, depth, Qp in ((320.0, 16.0, 1.2), (320.0, 33.0, 4.0), (330.0, 16.0, 0.7),
                          (300.0, 20.0, 2.0)):
        b, a = P.notch_ba(f0, depth, Qp, A.FS)
        w = np.exp(1j * 2.0 * np.pi * FNOTCH / A.FS)
        Hs = ((b[0] + b[1] / w + b[2] / w ** 2) / (a[0] + a[1] / w + a[2] / w ** 2))
        mag = 20.0 * np.log10(np.abs(Hs))
        # closed form: |H| dips to 10^(-depth/20) at f0 and the half-depth contour is at
        # -depth/2 dB, so the TRUE width is found on a 100x finer grid of the same expression.
        ff = np.arange(180.0, 500.001, 0.0025)
        wf = np.exp(1j * 2.0 * np.pi * ff / A.FS)
        mf = 20.0 * np.log10(np.abs((b[0] + b[1] / wf + b[2] / wf ** 2)
                                    / (a[0] + a[1] / wf + a[2] / wf ** 2)))
        sh = float(np.max(mf[(ff >= P.SHOULDER_WIN[0]) & (ff <= P.SHOULDER_WIN[1])]))
        sel = (ff >= P.WIDTH_WIN[0]) & (ff <= P.WIDTH_WIN[1])
        cont = sh - 0.5 * (sh - float(np.min(mf[sel])))
        idx = np.flatnonzero(mf[sel] < cont)
        true_w = float(ff[sel][idx[-1]] - ff[sel][idx[0]])
        _, got = P.notch_width(FNOTCH, mag)
        err = 100.0 * (got - true_w) / true_w
        print("      %8.1f %8.1f %10.2f %10.2f %+9.2f" % (f0, depth, true_w, got, err))
        ok &= abs(err) < 5.0
    print("      => %s" % ("OK -- width is recovered to <5 %% at every synthesised null" if ok
                           else "FAIL -- the width statistic itself is not trustworthy"))
    return ok


# =============================================================================================
# GATE C -- the python->render calibration, tested OUT OF SAMPLE
# =============================================================================================
RENDER = "build/OfflineRender_artefacts/Release/OfflineRender"
# ⚠⚠ Taken from attack_render_gate, which DERIVES it from the capture filename rather than
# hand-writing it (session 65). The hand-written version omitted `--grunt`, so every render this
# tool made -- including GATE C's calibration anchor -- ran at GRUNT BOOST against captures taken
# at GRUNT CUT, a ~36 Hz vs ~896 Hz first-order highpass. See attack_render_gate._base_args().
BASE_ARGS = RG.BASE                                                 # the record's own point
ATTACK_IDX = {"flat": "0", "boost": "1", "cut": "2"}


def render_cal():
    """Render the CALIBRATION anchor -- 3 throws, ~18 s each. Only needed once."""
    import subprocess
    os.makedirs(CALDIR, exist_ok=True)
    for pos in POSITIONS:
        out = os.path.join(CALDIR, "cal_%s.wav" % pos)
        cmd = [RENDER, A.ORIG, out] + BASE_ARGS + ["--attack", ATTACK_IDX[pos]]
        for f in CAL_FITS:
            cmd += ["--fit", f]
        print("  rendering %s ..." % out)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("render failed:\n%s\n%s" % (" ".join(cmd), r.stderr))
        RG.stamp(out, cmd)
    print("  ok.")


def rendered(tag, pos):
    """Read a render. `dflt_*`/`prop_*` come from attack_render_gate.py (same operating point,
    so nothing is re-rendered); `cal_*` is this tool's own calibration anchor.

    ⚠ EVERY read is condition-checked against its own `.args.json` stamp. GATE C mixes renders
    from two different producers, so a stale one on either side silently corrupts the calibration
    -- which is exactly what happened in session 65 when the `dflt`/`prop` side was re-rendered at
    the corrected GRUNT and this `cal_*` anchor was not (see `attack_render_gate.stamp`).
    """
    dirn = CALDIR if tag == "cal" else RENDER_DIR
    path = os.path.join(dirn, "%s_%s.wav" % (tag, pos))
    if not os.path.exists(path):
        sys.exit("missing %s -- run: %s"
                 % (path, "python3.11 analysis/attack_shape_screen.py --render-cal"
                    if tag == "cal" else "python3.11 analysis/attack_render_gate.py --both"))
    fits = CAL_FITS if tag == "cal" else (RG.PROPOSAL if tag == "prop" else [])
    expect = list(BASE_ARGS) + ["--attack", ATTACK_IDX[pos]]
    for f in fits:
        expect += ["--fit", f]
    RG.check_stamp(path, expect)
    orig = A.load(A.ORIG)
    x = A.load(path)
    x, _ = A.align(x, orig)
    f, m = A.transfer(A.seg_of(x, SEG), A.seg_of(orig, SEG))
    return P.locate_notch(f, m)


def calibrate(tag, base, rd, c5t):
    """(d_f0, d_depth, k_width) per throw: python = render + d, python = render * k."""
    cal = {}
    for pos in POSITIONS:
        r = rendered(tag, pos)
        f0, dep, w = notch_stats(solve(base, rd, c5t, pos, FNOTCH, ZNOTCH))
        cal[pos] = (f0 - r["f_bin"], dep - r["depth"], w / r["width_i"])
    return cal


def predict(cal, base, rd, c5t, tag):
    """Apply a calibration to the screen and compare against `tag`'s render."""
    rows, ok = {}, True
    for pos in POSITIONS:
        r = rendered(tag, pos)
        f0, dep, w = notch_stats(solve(base, rd, c5t, pos, FNOTCH, ZNOTCH))
        d0, dd, kw = cal[pos]
        pf, pd, pw = f0 - d0, dep - dd, w / kw
        rows[pos] = (pf, r["f_bin"], pd, r["depth"], pw, r["width_i"])
        ok &= (abs(pf - r["f_bin"]) < 3.0 and abs(pd - r["depth"]) < 1.5
               and abs(pw - r["width_i"]) / r["width_i"] < 0.12)
    return rows, ok


def gate_calibration():
    print("\n  C CALIBRATION out-of-sample, BOTH directions between two very different C8=0")
    print("      ladders. A calibration tested where it was fitted proves nothing (session 43).")
    cal_c = calibrate("cal", CAL, CAL_RD, CAL_C5T)
    cal_p = calibrate("prop", PROP, PROP_RD, PROP_C5T)
    print("      from CAL : %s"
          % " | ".join("%s df0 %+.2f dep %+.2f kw %.3f" % (p, *cal_c[p]) for p in POSITIONS))
    print("      from PROP: %s"
          % " | ".join("%s df0 %+.2f dep %+.2f kw %.3f" % (p, *cal_p[p]) for p in POSITIONS))
    ok = True
    for cal, base, rd, c5t, tag, lab in ((cal_c, PROP, PROP_RD, PROP_C5T, "prop", "CAL -> PROP"),
                                         (cal_p, CAL, CAL_RD, CAL_C5T, "cal", "PROP -> CAL")):
        rows, good = predict(cal, base, rd, c5t, tag)
        ok &= good
        print("      %-11s %-6s | %-24s | %-24s | %s"
              % (lab, "throw", "f0 Hz pred/rend", "depth dB pred/rend", "width Hz pred/rend"))
        for pos in POSITIONS:
            pf, rf, pd, rdp, pw, rw = rows[pos]
            print("      %-11s %-6s | %7.2f /%7.2f (%+5.2f) | %7.2f /%7.2f (%+5.2f) |"
                  " %6.1f /%6.1f (%+5.1f%%)"
                  % ("", pos, pf, rf, pf - rf, pd, rdp, pd - rdp, pw, rw,
                     100.0 * (pw - rw) / rw))
    print("      => %s" % (
        "OK -- one calibration transfers between two very different ladder points"
        if ok else "CHECK -- the calibration does NOT transfer well enough to fit ABSOLUTE width\n"
                   "                on. Treat the screen as a LEVER FINDER and land every value on\n"
                   "                attack_render_gate.py (which is the arbiter regardless)."))
    # The PROP-anchored calibration is the one used for targets: it is anchored at the point
    # the fit starts from, so first-order it is exact there.
    return cal_p, ok


# =============================================================================================
# targets, expressed in the SCREEN's own units via the calibration
# =============================================================================================
def screen_targets(cal):
    """The pedal's requirement mapped into python-solve units."""
    d = REC["raw"]["notch"]
    t = {}
    for pos in POSITIONS:
        d0, dd, kw = cal[pos]
        t[pos] = (float(d[pos]["f_bin"]) + d0,
                  float(d[pos]["depth"]) + dd,
                  float(d[pos]["width_i"]) * kw)
    return t


# =============================================================================================
# the fit
# =============================================================================================
SHARED = ["R7", "R12", "R14", "C5", "C9", "C6", "C7"]
TAP = ["Ra", "Rb", "Rc", "R11"]
BOX = 1.0                                                 # decades, each side (see box_sweep)
# ⚠ The record quotes f0 on the 5.86 Hz measurement grid, so an f0 rms below a quarter bin is
# not a real difference between two candidates -- see the ranking note in best_point().
F0_TIE_BINS = 0.25


def build(x, shared, fit_tap):
    """x = [shared multipliers..., Rd per throw..., C5trim per throw..., tap multipliers...]"""
    base = dict(PROP)
    k = 0
    for e in shared:
        base[e] = PROP[e] * 10.0 ** x[k]; k += 1
    rd = {}
    for pos in POSITIONS:
        rd[pos] = PROP_RD[pos] * 10.0 ** x[k]; k += 1
    c5t = {}
    for pos in POSITIONS:
        # Trims are ADDITIVE parallel caps on the same pole (session 62 item 7), so they must
        # stay >= 0. ⚠ Mapped LINEARLY onto [0, 0.3*C5] rather than as a log multiplier: a
        # `max(0, C5*(10**x - 1))` form (a first draft) sends the whole negative half of the box
        # to exactly 0, i.e. half the search space is one flat point -- a self-inflicted
        # degeneracy of the kind session 52 item 3(c) had to diagnose in real data.
        c5t[pos] = base["C5"] * 0.3 * 0.5 * (x[k] / BOX + 1.0); k += 1
    if fit_tap:
        for e in TAP:
            base[e] = PROP[e] * 10.0 ** x[k]; k += 1
    return base, rd, c5t


def ndim(shared, fit_tap):
    return len(shared) + 2 * len(POSITIONS) + (len(TAP) if fit_tap else 0)


class Cost:
    """Notch triple in the screen's units + the broadband h ABSOLUTELY (no free scalar).

    `w_f0` scales the f0 term ONLY, so the f0-vs-width conflict can be traced as a PARETO
    FRONTIER instead of being hidden inside one weighted number (session 49/52's move: report
    the frontier, because a single weight silently picks a trade for you).
    """

    def __init__(self, shared, tgt, fit_tap=True, wt_bb=1.0, override=None, w_f0=1.0):
        self.shared, self.tgt, self.fit_tap, self.wt_bb = list(shared), tgt, fit_tap, wt_bb
        self.override, self.w_f0 = override, w_f0

    def parts(self, x):
        base, rd, c5t = build(x, self.shared, self.fit_tap)
        st = full_stats(base, rd, c5t)
        if st is None:
            return None
        t = self.override if self.override is not None else self.tgt
        f0r, depr, wr = [], [], []
        for pos in POSITIONS:
            f0, dep, w = st["notch"][pos]
            tf0, tdep, tw = t[pos]
            f0r.append((f0 - tf0) / M.BIN_HZ)                  # bins
            depr.append((dep - tdep) / M.DEPTH_FLOOR_DB)       # dB, floor 1 dB (a bound)
            wr.append((w - tw) / (0.10 * tw))                  # 10 % of the target width
        br = np.concatenate([REC["h"][q] - st["h"][q] for q in THROWS]) / REC["floor"]
        rms = lambda v: float(np.sqrt(np.mean(np.square(v))))   # noqa: E731
        return (rms(f0r + depr + wr), rms(br), st, rms(f0r), rms(wr), rms(depr))

    def __call__(self, x):
        r = self.parts(x)
        if r is None:
            return 1e6
        _, b, _, f0, w, dep = r
        n = float(np.sqrt((self.w_f0 * f0 * f0 + w * w + dep * dep) / (self.w_f0 + 2.0)))
        return float(np.sqrt((n * n + self.wt_bb * b * b) / (1.0 + self.wt_bb)))


def run(shared, tgt, fit_tap=True, quick=False, seed=17, override=None, wt_bb=1.0, w_f0=1.0,
        box=None):
    c = Cost(shared, tgt, fit_tap, wt_bb, override, w_f0)
    nd = ndim(shared, fit_tap)
    box = BOX if box is None else box
    r = differential_evolution(c, [(-box, box)] * nd, seed=seed,
                               maxiter=80 if quick else 200, popsize=12 if quick else 20,
                               tol=1e-10, polish=True, init="sobol", workers=-1,
                               updating="deferred")
    return r.fun, r.x, c.parts(r.x)


def frontier(tgt, quick):
    """⭐ THE DECIDING MEASUREMENT. Is the width reachable WHILE the notch triple is held?

    The tap is PINNED here, and that is not a shortcut -- the census proves it moves width by
    <=0.5 Hz and f0 by 0.00 Hz, so it carries no notch information at all, and session 62 item 4
    established the rule: when a joint objective under-delivers on one requirement, SEPARATE the
    fits before calling it unreachable, because scoring non-interacting groups jointly buys
    nothing and costs arbitration. The broadband is therefore dropped from this objective too
    (wt_bb = 0) and re-checked afterwards with the tap free.

    Sweeping the f0 weight traces the frontier: if a point exists with f0 held to the bin AND the
    width right, some weight finds it. If instead width is stuck near its current value whenever
    f0 is held, the two requirements are in CONFLICT inside this topology -- which is a structural
    statement, not a fit failure.
    """
    print("\n" + "=" * 104)
    print("⭐ THE FRONTIER -- can WIDTH be reached while the NOTCH TRIPLE is held? (tap PINNED:")
    print("   the census says it carries no notch information, so scoring it here only arbitrates)")
    print("=" * 104)
    print("  %6s | %8s %8s %8s | %-22s | %s"
          % ("w_f0", "f0 rms", "width", "depth", "f0 cut/boost/flat Hz", "width cut/boost/flat Hz"))
    print("  %6s | %8s %8s %8s | want %5.1f %5.1f %5.1f    | want %5.1f %5.1f %5.1f"
          % ("", "(bins)", "(rms)", "(rms)",
             *[tgt[p][0] for p in POSITIONS], *[tgt[p][2] for p in POSITIONS]))
    rows = []
    for w_f0 in (0.0, 0.3, 1.0, 3.0, 10.0, 100.0):
        c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=w_f0)
        if parts is None:
            continue
        _, _, st, rf0, rw, rdep = parts
        f0s = [st["notch"][p][0] for p in POSITIONS]
        ws = [st["notch"][p][2] for p in POSITIONS]
        print("  %6.1f | %8.2f %8.2f %8.2f | %6.1f %6.1f %6.1f  | %6.1f %6.1f %6.1f  (spread %.1f Hz)"
              % (w_f0, rf0, rw, rdep, *f0s, *ws, max(f0s) - min(f0s)))
        rows.append(dict(w_f0=w_f0, f0_rms=rf0, w_rms=rw, dep_rms=rdep,
                         f0=f0s, width=ws, spread=max(f0s) - min(f0s),
                         x=[float(v) for v in x]))
    print("\n  required f0 spread = %.2f Hz (the pedal's, session 61). The DRAWN topology gives"
          % (max(tgt[p][0] for p in POSITIONS) - min(tgt[p][0] for p in POSITIONS)))
    print("  0.00 Hz and session 61 found 0 of 782 random draws reproducing the pedal's pattern,")
    print("  so a fit that reaches the width by COLLAPSING the spread has given up the requirement")
    print("  that made the two-pole topology necessary in the first place -- read the spread column.")

    # ⭐⭐ THE BOX SWEEP. A large residual with all 13 values free is only readable as
    # UNREACHABILITY if widening the search does not shrink it. Session 57 item 4's own test:
    # there the cost moved 0.001 dB across 7.5 orders of magnitude of box widening, which is what
    # "the objective cannot reach this direction" looks like. Run at the weight that scores all
    # nine numbers equally.
    print("\n  BOX SWEEP at w_f0 = 1 (all 9 numbers scored equally, %d free values):"
          % ndim(SHARED, False))
    print("  %8s | %8s %8s %8s %8s | %s" % ("box", "cost", "f0 rms", "width", "depth", "on a bound"))
    sweep = []
    for box in (0.5, 1.0, 2.0, 3.0):
        c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=1.0, box=box)
        if parts is None:
            continue
        names = list(SHARED) + ["Rd " + p for p in POSITIONS] + ["C5t " + p for p in POSITIONS]
        ob = [e for e, xi in zip(names, x) if abs(abs(xi) - box) < 0.03 * box]
        print("  %8.1f | %8.4f %8.2f %8.2f %8.2f | %s"
              % (box, c, parts[3], parts[4], parts[5], ", ".join(ob) if ob else "-"))
        sweep.append(dict(box=box, cost=float(c), f0_rms=parts[3], w_rms=parts[4],
                          dep_rms=parts[5], on_bound=ob))
    if len(sweep) > 1:
        span = max(s["cost"] for s in sweep) - min(s["cost"] for s in sweep)
        print("  ⇒ cost moves %.4f across %.0fx of box widening in EVERY one of %d free values."
              % (span, (sweep[-1]["box"] / sweep[0]["box"]), ndim(SHARED, False)))
        print("    %s" % ("SATURATED -- read the residual as UNREACHABILITY, not a weak search."
                          if span < 0.35 else
                          "NOT saturated -- the search is still finding room; do not call this "
                          "unreachable yet."))
    return dict(frontier=rows, box_sweep=sweep)


# =============================================================================================
# ⭐⭐ WHY the conflict, if there is one: the ladder is exactly frequency-scale-invariant, and
# exactly ONE cap in the path cannot be scaled with it.
# =============================================================================================
def scale_diagnostic(tgt, quick):
    """Localise the f0-vs-width conflict to the J201 drain pole.

    THE ALGEBRA. This network is R and C only, so scaling EVERY capacitance by 1/k with every
    resistance fixed maps H(s) -> H(ks) exactly: the curve is translated in frequency with its
    SHAPE (and therefore every Q, every half-depth width in octaves) untouched. That is the same
    scale invariance A2c-3 used to make the mid stage constant-Q at all three switch positions.

    ⇒ If the shape were reachable at ANY frequency, it would be reachable at the RIGHT frequency,
    just by scaling the caps -- unless some capacitance in the path cannot be scaled. Three caps
    are candidates: C5/C9/C6 (the ladder, free), C7 (the coupling cap, free) and `Cp` -- the
    J201 drain network's own pole, Rp*Cp = R6*C3, which is NOT part of the treble stage at all.
    It is the JfetStage boundary, anchored by session 4's gm fit, and its corner sits at
    ~220-720 Hz, i.e. INSIDE the notch region.

    So this runs the frontier's own objective twice: once as shipped, and once with a single extra
    free value that scales `Cp` together with the ladder caps. ⚠ THE SECOND RUN IS A DIAGNOSTIC,
    NOT A PROPOSAL -- Cp is the J201 boundary and moving it is a claim about the JFET, not about
    ATTACK. It is here to answer WHERE the constraint lives, exactly as session 40 used a
    rails-off render to localise a level-axis residual without proposing to ship rails off.
    """
    print("\n" + "=" * 104)
    print("⭐⭐ WHERE THE CONSTRAINT LIVES -- the ladder is scale-invariant, so a shape reachable at")
    print("   ANY frequency is reachable at the RIGHT one, UNLESS an unscalable cap is in the path.")
    print("   The only one is the J201 drain's Cp (Rp*Cp = R6*C3, corner ~220-720 Hz = in the notch")
    print("   region). ⚠ Freeing it is a DIAGNOSTIC, not a proposal: it is the JfetStage boundary.")
    print("=" * 104)
    rows = {}
    for lab, free_cp in (("Cp FIXED (as shipped)", False), ("Cp scalable (DIAGNOSTIC)", True)):
        best = None
        for kscale in ([0.0] if not free_cp else [-0.30, -0.20, -0.10, 0.0, 0.10, 0.20]):
            zs = ZNOTCH if not free_cp else E.jfet_source_z(
                FNOTCH, **dict(M.ZS, C3=220.0e-9 * 10.0 ** kscale))
            global ZNOTCH_OVERRIDE
            ZNOTCH_OVERRIDE = zs
            c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=1.0)
            ZNOTCH_OVERRIDE = None
            if parts is None:
                continue
            if best is None or c < best[0]:
                best = (c, kscale, parts)
        if best is None:
            continue
        c, kscale, parts = best
        f0s = [parts[2]["notch"][p][0] for p in POSITIONS]
        ws = [parts[2]["notch"][p][2] for p in POSITIONS]
        print("  %-26s cost %.4f | f0 rms %.2f bins  width rms %.2f  depth rms %.2f"
              % (lab, c, parts[3], parts[4], parts[5]))
        print("  %-26s f0 %6.1f %6.1f %6.1f (spread %.1f)  width %6.1f %6.1f %6.1f%s"
              % ("", *f0s, max(f0s) - min(f0s), *ws,
                 "" if not free_cp else "   C3 x%.2f" % (10.0 ** kscale)))
        rows[lab] = dict(cost=float(c), f0_rms=parts[3], w_rms=parts[4], dep_rms=parts[5],
                         f0=f0s, width=ws, c3_scale=10.0 ** kscale)
    print("  want%22s f0 %6.1f %6.1f %6.1f (spread %.1f)  width %6.1f %6.1f %6.1f"
          % ("", *[tgt[p][0] for p in POSITIONS],
             max(tgt[p][0] for p in POSITIONS) - min(tgt[p][0] for p in POSITIONS),
             *[tgt[p][2] for p in POSITIONS]))
    if len(rows) == 2:
        a, b = [rows[k]["cost"] for k in rows]
        print("\n  ⇒ %s" % ("freeing Cp does NOT relieve the conflict (%.4f -> %.4f), so the "
                            "constraint is\n    NOT the J201 drain pole -- look elsewhere."
                            % (a, b) if b > 0.75 * a else
                            "freeing Cp RELIEVES the conflict (%.4f -> %.4f) ⇒ the notch's absolute\n"
                            "    frequency is pinned against the J201 DRAIN POLE, and the ladder can "
                            "set the\n    null's frequency or its Q but not both. That is a "
                            "PRE-treble constraint, not an\n    ATTACK one -- and it is a NEW place "
                            "to look, not a value to ship." % (a, b)))
    return rows


def show(tag, cost, x, parts, shared, fit_tap, tgt):
    n, b, st = parts[0], parts[1], parts[2]
    print("\n  %s" % tag)
    print("    cost %.4f   (notch %.4f, broadband %.4f)   dof %d vs 9 notch numbers"
          % (cost, n, b, ndim(shared, fit_tap)))
    print("    %-6s | %-22s | %-22s | %s"
          % ("throw", "f0 Hz  got / want", "depth dB  got / want", "width Hz  got / want"))
    for pos in POSITIONS:
        f0, dep, w = st["notch"][pos]
        tf0, tdep, tw = tgt[pos]
        print("    %-6s | %7.2f / %7.2f (%+5.2f) | %7.2f / %7.2f (%+5.2f) | %6.1f / %6.1f (%+5.1f%%)"
              % (pos, f0, tf0, f0 - tf0, dep, tdep, dep - tdep, w, tw, 100.0 * (w - tw) / tw))
    for q in THROWS:
        med, slp = st["shape"][q]
        pm = float(np.median(REC["h"][q]))
        print("    h %-4s median %+6.2f (pedal %+6.2f)   slope %+6.2f dB/dec"
              % (q, med, pm, slp))
    base, rd, c5t = build(x, shared, fit_tap)
    # ⚠ bound-check EVERY free value, not just the shared ones. A first draft checked only
    # `shared` and the TAP was quietly running to x1/10 (x ~= -0.975 of a 1-decade box) --
    # a parameter on its bound is unidentified, not a value (bound-resting-means-unidentified).
    names = list(shared) + ["Rd " + p for p in POSITIONS] + ["C5t " + p for p in POSITIONS] \
        + (TAP if fit_tap else [])
    on_bound = [e for e, xi in zip(names, x) if abs(abs(xi) - BOX) < 0.03]
    print("    shared: %s" % "  ".join("%s %.3g (x%.2f)" % (e, base[e], base[e] / PROP[e])
                                       for e in shared))
    print("    per throw Rd: %s" % "  ".join("%s %.0f" % (p, rd[p]) for p in POSITIONS))
    print("    per throw C5: %s" % "  ".join("%s %.3g" % (p, base["C5"] + c5t[p])
                                             for p in POSITIONS))
    if fit_tap:
        print("    tap: %s" % "  ".join("%s %.3g" % (e, base[e]) for e in TAP))
    if on_bound:
        print("    ⚠ ON A BOUND (unidentified, not a value): %s" % ", ".join(on_bound))
    return dict(cost=cost, notch=n, broadband=b, on_bound=on_bound,
                got={p: list(st["notch"][p]) for p in POSITIONS},
                shape={q: list(st["shape"][q]) for q in THROWS},
                shared={e: base[e] for e in shared},
                rd=dict(rd), c5={p: base["C5"] + c5t[p] for p in POSITIONS},
                tap=({e: base[e] for e in TAP} if fit_tap else None))


# =============================================================================================
def grunt_term(orig, curve):
    """The GRUNT coupling's OWN contribution to the 200 -> 480 Hz drop, MEASURED.

    Rendered twice at the drawn defaults, identical but for `--grunt`: CUT (the captures'
    position, ~896 Hz first-order corner) minus BOOST (~36 Hz, i.e. essentially flat across this
    window). The difference of the two drops IS the GRUNT term, with everything else in the chain
    cancelling exactly. Cached -- it is one 18 s render and it never changes.
    """
    import subprocess
    path = os.path.join(RENDER_DIR, "gruntctl_boost.wav")
    if not os.path.exists(path):
        os.makedirs(RENDER_DIR, exist_ok=True)
        cmd = ([RENDER, A.ORIG, path]
               + [("0" if a == "1" and BASE_ARGS[i - 1] == "--grunt" else a)
                  for i, a in enumerate(BASE_ARGS)]
               + ["--attack", ATTACK_IDX["flat"]])
        print("  (rendering the GRUNT control %s ...)" % path)
        r = subprocess.run(cmd, capture_output=True, text=True)
        if r.returncode != 0:
            sys.exit("GRUNT control render failed:\n%s\n%s" % (" ".join(cmd), r.stderr))
        RG.stamp(path, cmd)

    def drop(p):
        x = A.load(p)
        x, _ = A.align(x, orig)
        f, m = curve(x, "sweep_clean_-36")
        i = int(np.argmin(np.abs(f - 200.0)))
        j = int(np.argmin(np.abs(f - 480.0)))
        return float(m[j] - m[i])

    return drop(os.path.join(RENDER_DIR, "dflt_flat.wav")) - drop(path)


def tilt_probe():
    """⭐⭐ IS THE WIDTH RESIDUAL EVEN ATTACK'S? Measure the OD path's OWN absolute shape.

    `h` is a RATIO between throws, so everything shared by all three cancels out of it by
    construction -- which is exactly why every ATTACK instrument since session 57 has been blind
    to a shared error. But WIDTH is not a ratio: it is measured on ONE throw's own magnitude,
    against that throw's own 200-270 Hz shoulder, so the ABSOLUTE shape through the notch window
    is inside it. So compare that shape directly, pedal vs model, each referred to its own 200 Hz
    value. Bleed-free by topology at LEVEL max / BLEND max (render gate GATE 3).

    Two gates on the reading itself, both from this project's own history:
      * it must be present in ALL THREE throws, or it is not a shared error;
      * it must be LEVEL-independent, or it is an operating point (session 61 item 3).

    Then the mechanism test: remove ONLY the tilt DIFFERENCE (a first-order rotation about
    200 Hz, which cannot create or destroy a null) and re-measure the width with the same
    locator. ⚠ That test REFUTED the obvious hypothesis when it was run (session 64): the tilt
    accounts for about a quarter of the width excess, not for it. Reported either way.

    ⚠⚠ WHAT THIS PROBE FIRST REPORTED, AND WHY IT WAS WRONG -- session 65, kept because the
    failure mode is general. On its first run (session 64) it read PEDAL -4.88 vs MODEL -11.05 dB
    and concluded a 6.2 dB shape error attributable to the IC2_B bridged-T, i.e. GAP #1b reopened.
    The renders it read were made by attack_render_gate.py, whose operating point was hand-written
    as four flags -- and the flag it did NOT write, `--grunt`, fell back to OfflineRender's default
    of 0 = BOOST while every capture here is GRUNT CUT. That is a first-order highpass at ~36 Hz
    instead of ~896 Hz, worth ~6.7 dB of slope across exactly this window. The whole finding was
    the missing flag. At the captures' own GRUNT the model drops -4.02 / -3.71 / -3.93 against the
    pedal's -4.92 / -5.32 / -4.87, i.e. ~1 dB and in the OPPOSITE direction (the model's scoop is
    slightly SHALLOWER), which is the same direction session 21 closed GAP #1b on.
    ⭐ TWO GENERAL LESSONS, both already in this project's own rules and both re-learned here:
      * the probe's two soundness gates -- present in all three throws, level-independent -- are
        satisfied EXACTLY as well by a shared render-condition error as by a shared circuit error,
        so neither gate could ever have caught this. What catches it is asserting that the render
        condition IS the capture's condition (attack_render_gate GATE 0), which is now done by
        deriving the flags from `captures.render_args` rather than typing them.
      * this function's verdict paragraph was NARRATED, so it kept asserting "the bridged-T
        accounts for it to 0.26 dB" above a table that no longer said that. Every number in the
        verdict is now COMPUTED from the run (`computed-verdicts-not-narrated`, third occurrence).
    """
    print("\n" + "=" * 104)
    print("⭐⭐ IS THE WIDTH RESIDUAL EVEN ATTACK'S? -- the OD path's OWN shape, 200 -> 480 Hz")
    print("   (h is a ratio and cancels everything shared; WIDTH is not a ratio and does not)")
    print("=" * 104)
    orig = A.load(A.ORIG)
    with redirect_stdout(io.StringIO()):
        caps = P.load_all(orig)

    def curve(x, seg):
        return A.transfer(A.seg_of(x, seg), A.seg_of(orig, seg))

    def read(f, m):
        i = int(np.argmin(np.abs(f - 200.0)))
        j = int(np.argmin(np.abs(f - 480.0)))
        sel = (f >= 180.0) & (f <= 500.0)
        ex = sel & ~((f >= P.NOTCH_EXCLUDE[0]) & (f <= P.NOTCH_EXCLUDE[1]))
        return float(m[j] - m[i]), float(np.polyfit(np.log10(f[ex]), (m - m[i])[ex], 1)[0])

    def rendered_curve(tag, pos, seg):
        path = os.path.join(RENDER_DIR, "%s_%s.wav" % (tag, pos))
        expect = list(BASE_ARGS) + ["--attack", ATTACK_IDX[pos]]
        for f in (RG.PROPOSAL if tag == "prop" else []):
            expect += ["--fit", f]
        RG.check_stamp(path, expect)          # a render from another condition is not a datum
        x = A.load(path)
        x, _ = A.align(x, orig)
        return curve(x, seg)

    print("  drop over 200->480 Hz, and the ex-null slope, per throw and per LEVEL:")
    print("  %-14s %-22s %-22s" % ("", "-36 dBFS drop / slope", "-30 dBFS drop / slope"))
    rows = {}
    for pos in POSITIONS:
        a = read(*curve(caps[pos], "sweep_clean_-36"))
        b = read(*curve(caps[pos], "sweep_clean"))
        rows["PEDAL " + pos] = b
        print("  %-14s %+9.2f / %+9.2f  %+9.2f / %+9.2f" % ("PEDAL " + pos, *a, *b))
    for tag in ("dflt", "prop"):
        for pos in POSITIONS:
            a = read(*rendered_curve(tag, pos, "sweep_clean_-36"))
            b = read(*rendered_curve(tag, pos, "sweep_clean"))
            rows["%s %s" % (tag, pos)] = b
            print("  %-14s %+9.2f / %+9.2f  %+9.2f / %+9.2f" % (tag + " " + pos, *a, *b))

    # ---- WHICH ELEMENT: a CLOSED accounting, not a single-element attribution ----------------
    # ⚠ The GRUNT coupling is a first-order highpass at ~896 Hz in the CUT position, so it is
    # worth several dB across this very window and must appear in the sum. Session 64's version
    # omitted it -- and, because its renders were accidentally at GRUNT BOOST (~36 Hz, i.e. flat
    # here), omitting it happened to close. It does not close at the captures' own GRUNT unless
    # the term is there. It is MEASURED, not modelled: the same render at `--grunt 0`.
    bt = E.bridged_t_tf(np.array([200.0, 480.0]))
    btd = float(20.0 * np.log10(np.abs(bt[1]) / np.abs(bt[0])))
    sk = [E.sallen_key_lpf_tf(np.array([200.0, 480.0]), 10e3, 22e3, 1e-9, 1e-9),
          E.sallen_key_lpf_tf(np.array([200.0, 480.0]), 22e3, 47e3, 2.2e-9, 1e-9)]
    skd = sum(float(20.0 * np.log10(np.abs(s[1]) / np.abs(s[0]))) for s in sk)
    gd = grunt_term(orig, curve)
    tot = rows["dflt flat"][0]
    acct = btd + skd + gd
    print("\n  WHICH ELEMENT -- every named contribution to the DRAWN model's own drop, summed:")
    print("    IC2_B bridged-T (analytic)      %+7.2f dB" % btd)
    print("    two Sallen-Keys (analytic)      %+7.2f dB" % skd)
    print("    GRUNT cut coupling (measured)   %+7.2f dB   <- absent from session 64's accounting"
          % gd)
    print("    %-30s %+7.2f dB" % ("SUM", acct))
    print("    %-30s %+7.2f dB   residual %.2f dB" % ("MODEL, measured", tot, abs(acct - tot)))
    print("  ⇒ the bridged-T is still the only element with real authority here (%.1fx the SKs),"
          % (abs(btd) / max(abs(skd), 1e-9)))
    print("    but it is opposed by the GRUNT highpass, and the two nearly cancel.")
    resid = rows["PEDAL flat"][0] - tot
    print("\n  PEDAL %+.2f dB vs MODEL %+.2f ⇒ residual %+.2f dB (floor ~%.2f). %s"
          % (rows["PEDAL flat"][0], tot, resid, 2.0 * P.DIFF_FLOOR,
             "The model's scoop is SHALLOWER than the pedal's through this window."
             if resid < 0 else "The model's scoop is DEEPER than the pedal's here."))
    print("  ⚠ Session 64 read this as %+.1f dB with the model far DEEPER and reopened GAP #1b on"
          % -6.2)
    print("    it; that was the missing --grunt flag (see the docstring). The sign here agrees")
    print("    with session 21's closure, which also found the plugin's dip ~0.5 dB SHALLOWER.")

    print("\n  MECHANISM TEST -- does the excess tilt EXPLAIN the ~2x width? Rotate each model")
    print("  curve about 200 Hz until its ex-null background slope equals the pedal's, then")
    print("  re-measure the width with the SAME locator. A rotation cannot create/destroy a null.")
    print("  %-14s %10s %10s %10s %12s" % ("throw", "width now", "de-tilted", "PEDAL", "ratio after"))
    out = {}
    for tag in ("dflt", "prop"):
        for pos in POSITIONS:
            fm, mm = rendered_curve(tag, pos, "sweep_clean")
            fp, mp = curve(caps[pos], "sweep_clean")
            _, sm = read(fm, mm)
            _, sp = read(fp, mp)
            corr = (sp - sm) * np.log10(fm / 200.0)
            w0 = P.notch_width(fm, mm)[1]
            w1 = P.notch_width(fm, mm + corr)[1]
            wp = P.notch_width(fp, mp)[1]
            print("  %-14s %10.1f %10.1f %10.1f %11.2fx"
                  % (tag + " " + pos, w0, w1, wp, w1 / wp))
            out["%s %s" % (tag, pos)] = dict(w=w0, w_detilted=w1, w_pedal=wp,
                                             ratio_before=w0 / wp, ratio_after=w1 / wp)
    pb = [out["prop %s" % p]["ratio_before"] for p in POSITIONS]
    pa = [out["prop %s" % p]["ratio_after"] for p in POSITIONS]
    print("\n  ⇒ de-tilting moves the PROPOSAL's ratio %s -> %s, so the excess tilt is worth"
          % ("/".join("%.2f" % v for v in pb), "/".join("%.2f" % v for v in pa)))
    print("    about %.0f %% of the width excess and the rest is a genuine null-Q difference."
          % (100.0 * (1.0 - (np.mean(pa) - 1.0) / max(np.mean(pb) - 1.0, 1e-9))))
    print("    ⚠ The tempting reading -- that the tilt excess and the width excess are the same")
    print("    ~2x, so one causes the other -- is REFUTED by this test. Coincidence.")
    print("  ⇒ AND THE TILT ITSELF IS NOW SMALL: %+.2f dB (flat throw), against session 64's"
          % resid)
    print("    -6.2 dB. GAP #1b stays CLOSED; what remains is the null-Q difference above,")
    print("    which is ATTACK's network and not the bridged-T's.")
    return dict(drop_slope={k: list(v) for k, v in rows.items()},
                bridged_t_drop=btd, sk_drop=skd, grunt_drop=gd, accounted=acct,
                model_drop=tot, residual=resid, detilt=out)


class TapCost:
    """The broadband h alone, with the notch section frozen. Module level so it can be pickled
    by differential_evolution(workers=-1)."""

    def __init__(self, base, rd, c5t):
        self.base, self.rd, self.c5t = dict(base), dict(rd), dict(c5t)

    def __call__(self, xt):
        b2 = dict(self.base)
        for e, xi in zip(TAP, xt):
            b2[e] = PROP[e] * 10.0 ** xi
        st = full_stats(b2, self.rd, self.c5t)
        if st is None:
            return 1e6
        br = np.concatenate([REC["h"][q] - st["h"][q] for q in THROWS]) / REC["floor"]
        return float(np.sqrt(np.mean(np.square(br))))


def best_point(tgt, quick, boxes=(1.0, 3.0)):
    """The best available compromise, with f0 weighted hard because f0 is the requirement that
    already matches TO THE BIN and the one session 61 proved the drawn topology cannot reach at
    all (0 of 782 draws).

    Two stages, because the census proves the groups do not interact (session 62 item 4's rule):
      1 NOTCH   shared ladder + per-throw pole B, tap PINNED, scored on the 9 notch numbers only.
      2 BROADBAND  tap alone re-fitted on h, with the notch section frozen -- the tap moves width
                by <=0.5 Hz and f0 by 0.00 Hz, so it cannot undo stage 1.

    ⚠⚠ THE SEARCH BOX IS NOW SWEPT, NOT FIXED AT 3.0 -- session 66. The old version searched box
    3.0 only, justified in its own header as "the sweep showed 1.0 was still constraining". That
    justification came from session 64's box sweep, which was run against a requirement transferred
    through a calibration built on a WRONG RENDER CONDITION (session 65: a missing `--grunt` flag).
    At the corrected calibration box 1.0 is NOT constraining -- it reaches the nine numbers with no
    element on a bound -- while box 3.0 wanders three decades out to values that are worse on the
    f0/width ranking AND unrealisable in FitParams. ⭐ GENERAL: a SEARCH SETTING justified by a
    measurement is as perishable as any other number derived from it; when the measurement is
    corrected the setting has to be re-derived, not carried. Sweeping removes the choice entirely
    and puts the comparison in the tool's own output, where the next session can see it.
    """
    print("\n" + "=" * 104)
    print("THE BEST AVAILABLE POINT -- box SWEPT (see the docstring: fixing it at 3.0 was")
    print("justified by session 64's now-void calibration), f0 weighted hard, then the tap")
    print("re-fitted on the broadband ALONE.")
    print("=" * 104)
    best, rows = None, []
    for box in boxes:
        for w_f0 in (1.0, 3.0, 10.0, 30.0, 100.0):
            c, x, parts = run(SHARED, tgt, fit_tap=False, quick=quick, wt_bb=0.0, w_f0=w_f0,
                              box=box)
            if parts is None:
                continue
            f0s = [parts[2]["notch"][p][0] for p in POSITIONS]
            ws = [parts[2]["notch"][p][2] for p in POSITIONS]
            nb = sum(1 for xi in x if abs(abs(xi) - box) < 0.03 * box)
            worst = max(abs(xi) for xi in x[:len(SHARED)])
            print("  box %4.1f w_f0 %6.1f | f0 rms %5.2f bins (spread %5.1f Hz) | width rms %5.2f"
                  " | widths %6.1f %6.1f %6.1f | worst shared x%.3g | %d on bound"
                  % (box, w_f0, parts[3], max(f0s) - min(f0s), parts[4], *ws, 10.0 ** worst, nb))
            # ⚠⚠ RANK f0 TO THE RESOLUTION THE RECORD HAS, NOT TO FULL PRECISION -- session 66.
            # A first version ranked on round(f0_rms, 2) and 0.06 bins beat 0.07 bins, which then
            # decided the winner AGAINST a point with 8.2 % width error in favour of one with
            # 12.7 %. 0.01 bins is 0.06 Hz; the pedal's f0 is quoted on a 5.86 Hz grid, so that
            # difference does not exist in the measurement. Anything at or under a QUARTER bin is
            # therefore treated as equally on-the-bin and width breaks the tie. ⭐ GENERAL: a
            # ranking key must be quantised to the resolution of the quantity it ranks, or search
            # noise in the tightest term silently outvotes a real difference in the next one.
            key = (max(round(parts[3], 2), F0_TIE_BINS), round(parts[4], 2), box)
            rows.append(dict(box=box, w_f0=w_f0, f0_rms=parts[3], w_rms=parts[4],
                             dep_rms=parts[5], f0=f0s, width=ws, spread=max(f0s) - min(f0s),
                             worst_shared=10.0 ** worst, n_on_bound=nb,
                             x=[float(v) for v in x]))
            if best is None or key < best[0]:
                best = (key, w_f0, x, parts, box)
    if best is None:
        return None
    _, w_f0, x, parts, box = best
    base, rd, c5t = build(x, SHARED, False)

    # ---- stage 2: the tap, on the broadband alone --------------------------------------------
    # ⚠ TapCost lives at MODULE level, not inside this function: differential_evolution(workers=-1)
    # pickles the objective across processes and a local class is unpicklable.
    rt = differential_evolution(TapCost(base, rd, c5t), [(-1.0, 1.0)] * len(TAP), seed=23,
                               maxiter=80 if quick else 200, popsize=12 if quick else 20,
                               tol=1e-10, polish=True, init="sobol", workers=-1,
                               updating="deferred")
    for e, xi in zip(TAP, rt.x):
        base[e] = PROP[e] * 10.0 ** xi
    st = full_stats(base, rd, c5t)
    print("\n  chosen (box = %.1f, w_f0 = %.0f), tap re-fitted on h alone (rms %.3f x floor):"
          % (box, w_f0, rt.fun))
    print("    %-6s | %-22s | %-22s | %s"
          % ("throw", "f0 Hz got/want", "depth dB got/want", "width Hz got/want"))
    for pos in POSITIONS:
        f0, dep, w = st["notch"][pos]
        tf0, tdep, tw = tgt[pos]
        print("    %-6s | %7.2f /%7.2f (%+5.2f) | %7.2f /%7.2f (%+5.2f) | %6.1f /%6.1f (%+5.1f%%)"
              % (pos, f0, tf0, f0 - tf0, dep, tdep, dep - tdep, w, tw, 100.0 * (w - tw) / tw))
    for q in THROWS:
        print("    h %-5s median %+6.2f (pedal %+6.2f)  slope %+6.2f dB/dec"
              % (q, st["shape"][q][0], float(np.median(REC["h"][q])), st["shape"][q][1]))
    names = list(SHARED) + ["Rd " + p for p in POSITIONS] + ["C5t " + p for p in POSITIONS]
    ob = [e for e, xi in zip(names, x) if abs(abs(xi) - box) < 0.03 * box] \
        + [e for e, xi in zip(TAP, rt.x) if abs(abs(xi) - 1.0) < 0.03]
    print("    shared: %s" % "  ".join("%s %.4g (x%.3g)" % (e, base[e], base[e] / PROP[e])
                                       for e in SHARED))
    print("    Rd: %s" % "  ".join("%s %.4g" % (p, rd[p]) for p in POSITIONS))
    print("    C5: %s" % "  ".join("%s %.4g" % (p, base["C5"] + c5t[p]) for p in POSITIONS))
    print("    tap: %s" % "  ".join("%s %.4g" % (e, base[e]) for e in TAP))
    if ob:
        print("    ⚠ ON A BOUND (unidentified, not a value): %s" % ", ".join(ob))

    # ⚠ The FitParams realisation makes trebleC5 the base and the two trims ADDITIVE parallel
    # caps, so both trims must be >= 0. The screen's three per-throw C5 values are unordered, so
    # rebase on the SMALLEST of them rather than on `flat` -- rebasing on flat can emit a negative
    # trim, which FitParams would silently clamp and the render would then not be the fitted point.
    c5min = min(c5t.values())
    fits = ["attackTapRa=%.6g" % base["Ra"], "attackTapRb=%.6g" % base["Rb"],
            "attackTapRc=%.6g" % base["Rc"], "attackTapR11=%.6g" % base["R11"],
            "trebleR7=%.6g" % base["R7"], "trebleLadderR12=%.6g" % base["R12"],
            "trebleLadderR14=%.6g" % base["R14"], "trebleC9=%.6g" % base["C9"],
            "trebleC6=%.6g" % base["C6"], "trebleC7=%.6g" % base["C7"],
            "trebleC5=%.6g" % (base["C5"] + c5min),
            "attackC5TrimBoost=%.6g" % (c5t["boost"] - c5min),
            "attackC5TrimCut=%.6g" % (c5t["cut"] - c5min),
            "trebleLadderDampR=%.6g" % rd["flat"], "attackDampBoost=%.6g" % rd["boost"],
            "attackDampCut=%.6g" % rd["cut"], "trebleC8=0"]
    if abs((base["C5"] + c5t["flat"]) - (base["C5"] + c5min)) > 1e-15:
        print("  ⚠ NOTE: flat is not the smallest C5, so trebleC5 is rebased on the smallest throw")
        print("    and the FLAT throw would need its own trim -- which FitParams does NOT have.")
        print("    That is a REALISABILITY gap in this candidate, recorded not hidden.")
    print("\n  as --fit (⚠ SCREEN units -- the RENDER is the arbiter, gate C says this screen is")
    print("  only a lever finder; land it with attack_render_gate.py --fits-json):")
    print("    " + " ".join("--fit " + f for f in fits))
    return dict(w_f0=w_f0, box=box, on_bound=ob, fits=fits, tap_bb_rms=float(rt.fun), rows=rows,
                got={p: list(st["notch"][p]) for p in POSITIONS},
                shape={q: list(st["shape"][q]) for q in THROWS})


def census(tgt):
    print("\n" + "=" * 104)
    print("SENSITIVITY CENSUS -- which SHARED element is a WIDTH lever, and is it width-SELECTIVE?")
    print("=" * 104)
    b = full_stats(PROP, PROP_RD, PROP_C5T)
    print("  at the proposal point, screen units: width cut/boost/flat %.1f / %.1f / %.1f Hz"
          % tuple(b["notch"][p][2] for p in POSITIONS))
    print("  target (pedal, mapped through the calibration):        %.1f / %.1f / %.1f Hz"
          % tuple(tgt[p][2] for p in POSITIONS))
    print("\n  %-5s %-5s | %8s %8s %8s | %9s %9s | %8s"
          % ("elem", "dir", "dw cut", "dw bst", "dw flt", "df0 flat", "ddep flat", "dh bst"))
    sel = {}
    for e in SHARED + TAP:
        for mult, lab in ((1.2, "+20%"), (0.8, "-20%")):
            p = dict(PROP); p[e] = PROP[e] * mult
            s = full_stats(p, PROP_RD, PROP_C5T)
            if s is None:
                continue
            dw = [s["notch"][q][2] - b["notch"][q][2] for q in POSITIONS]
            df = s["notch"]["flat"][0] - b["notch"]["flat"][0]
            dd = s["notch"]["flat"][1] - b["notch"]["flat"][1]
            dh = s["shape"]["boost"][0] - b["shape"]["boost"][0]
            print("  %-5s %-5s | %+8.1f %+8.1f %+8.1f | %+9.2f %+9.2f | %+8.2f"
                  % (e, lab, dw[0], dw[1], dw[2], df, dd, dh))
            if mult == 1.2:
                sel[e] = (float(np.mean(np.abs(dw))), abs(df), abs(dh))
    print("\n  ⭐ WIDTH-SELECTIVITY: width moved per Hz of f0 dragged. A lever that moves width only")
    print("     by moving f0 is not a width lever -- f0 already matches TO THE BIN and must not move.")
    print("  %-5s %10s %10s %14s %10s" % ("elem", "mean|dw|", "|df0|", "dw per Hz f0", "|dh bst|"))
    for e, (mw, df, dh) in sorted(sel.items(), key=lambda kv: -kv[1][0]):
        print("  %-5s %10.2f %10.3f %14s %10.2f"
              % (e, mw, df, ("%.1f" % (mw / df)) if df > 1e-3 else "inf (f0-neutral)", dh))
    return sel


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--census", action="store_true")
    ap.add_argument("--fit", action="store_true")
    ap.add_argument("--render-cal", action="store_true",
                    help="render the calibration anchor (3 throws, ~1 min); needed once")
    ap.add_argument("--best", action="store_true",
                    help="search the best available compromise and emit it as --fit")
    ap.add_argument("--tilt", action="store_true",
                    help="is the width residual even ATTACK's? the OD path's own absolute shape")
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--json", default=None)
    args = ap.parse_args()
    if args.render_cal:
        render_cal()
        if not (args.census or args.fit):
            return 0
    if not (args.census or args.fit or args.best or args.tilt):
        args.census = args.fit = True

    print("=" * 104)
    print("CAN THE TWO-POLE ATTACK TOPOLOGY MATCH THE NULL'S WIDTH? -- a SHARED-element screen")
    print("=" * 104)
    print("  solver: attack_tap_screen.tf_tap (8-node, gated there to ~1e-14 dB)")
    print("  stats : attack_notch_probe.locate_notch -- ONE definition, shared with the render gate")
    print("  grid  : %.2f Hz over %g-%g Hz for the null; the record's own bins for h"
          % (FNOTCH[1] - FNOTCH[0], FNOTCH[0], FNOTCH[-1]))

    print("\n" + "=" * 104)
    print("GATES")
    print("=" * 104)
    print("  A SOLVER      delegated to attack_tap_screen's own gate (not re-implemented here)")
    if not gate_width():
        return 1
    cal, cal_ok = gate_calibration()
    tgt = screen_targets(cal)
    print("\n  the requirement, in the screen's own units (f0 Hz / depth dB / width Hz):")
    for pos in POSITIONS:
        print("      %-6s %8.2f %8.2f %8.1f" % (pos, *tgt[pos]))

    out = dict(calibration={p: list(cal[p]) for p in POSITIONS}, cal_ok=bool(cal_ok),
               targets={p: list(tgt[p]) for p in POSITIONS})

    if args.tilt:
        out["tilt"] = tilt_probe()

    if args.census:
        out["census"] = {k: list(v) for k, v in census(tgt).items()}

    if args.best:
        print("\n" + "=" * 104)
        print("GATE D SEARCH -- recover a target this family DEFINITIONALLY makes")
        print("=" * 104)
        made = full_stats(dict(PROP, R12=PROP["R12"] * 1.7, C9=PROP["C9"] * 0.6),
                          dict(PROP_RD, boost=700.0), PROP_C5T)
        synth = {p: made["notch"][p] for p in POSITIONS}
        _, _, gparts = run(["R12", "C9"], tgt, fit_tap=False, quick=True, override=synth,
                           wt_bb=0.0)
        print("  recovering a self-generated (f0, depth, width) triple x3: cost %.5f  %s"
              % (gparts[0], "OK" if gparts[0] < 0.15 else "FAIL -- failures unreadable"))
        if gparts[0] >= 0.15:
            return 1
        out["best"] = best_point(tgt, args.quick)

    if args.fit:
        print("\n" + "=" * 104)
        print("GATE D SEARCH -- recover a target this family DEFINITIONALLY makes")
        print("=" * 104)
        made = full_stats(*(lambda b, r, c: (b, r, c))(
            dict(PROP, R12=PROP["R12"] * 1.7, C9=PROP["C9"] * 0.6),
            dict(PROP_RD, boost=700.0), PROP_C5T))
        synth = {p: made["notch"][p] for p in POSITIONS}
        # ⚠ wt_bb = 0: score the NOTCH ONLY. A first draft left the broadband term in with the
        # tap PINNED, so the objective also carried an unmatchable h residual and traded notch
        # accuracy against it -- it reported 0.857 and read as "weak optimiser" when it was the
        # gate's own construction. A search gate must ask exactly the question whose failure it
        # is meant to make readable (sessions 57/58/61 all had to tighten this same gate).
        c, x, parts = run(["R12", "C9"], tgt, fit_tap=False, quick=True, override=synth, wt_bb=0.0)
        print("  recovering a self-generated (f0, depth, width) triple x3: cost %.5f  %s"
              % (parts[0], "OK" if parts[0] < 0.15 else "FAIL -- weak optimiser, failures unreadable"))
        if parts[0] >= 0.15:
            return 1

        out["frontier"] = frontier(tgt, args.quick)
        out["scale_diagnostic"] = scale_diagnostic(tgt, args.quick)

        print("\n" + "=" * 104)
        print("THE FIT -- SMALLEST STRUCTURE FIRST. 6 per-throw dof already exist (Rd, C5 x3),")
        print("so a family with FEWER free values than the 9 notch numbers is real evidence;")
        print("one with more hits them by construction and is reported as such.")
        print("=" * 104)
        fits = {}
        for shared in ([], ["R12"], ["C9"], ["R7"], ["R12", "C9"], ["R7", "R12"],
                       ["R12", "C9", "C6"], SHARED):
            nd = ndim(shared, True)
            tag = "shared = %-28s (%d dof)" % ("{" + ", ".join(shared) + "}" if shared else "{}", nd)
            c, x, parts = run(shared, tgt, fit_tap=True, quick=args.quick)
            if parts is None:
                print("\n  %s -> pathological" % tag)
                continue
            fits[",".join(shared)] = show(tag + ("  ⚠ OVER-PARAMETERISED" if nd > 9 + 4 else ""),
                                         c, x, parts, shared, True, tgt)
        out["fits"] = fits

    if args.json:
        os.makedirs(os.path.dirname(args.json) or ".", exist_ok=True)
        json.dump(out, open(args.json, "w"), indent=1, default=float)
        print("\n  wrote %s" % args.json)
    return 0


if __name__ == "__main__":
    sys.exit(main())
